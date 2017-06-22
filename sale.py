# coding=utf-8
#This file is part of the sale_printery_budget module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.

from utils import *
from decimal import Decimal
import datetime
import uuid
from math import ceil
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.pyson import Eval, Id, Bool, Not
from trytond.transaction import Transaction
from trytond.wizard import Button, StateTransition, StateView, Wizard
from trytond.report import Report
from trytond.pool import PoolMeta
import logging
logger = logging.getLogger(__name__)

_all__ = ['Sale', 'SaleLine', 'OtraCantidad', 'CalcularPapelWizard',
    'CalcularPapelProducto', 'CalcularPapelElegirInterior',
    'PresupuestoClienteReport', 'CalcularPapel', 'RetomarCalcularPapel']

ORIENTACION = [
    ('', ''),
    ('frente', 'Frente'),
    ('dorso', 'Dorso'),
    ('frente_dorso', 'Frente/Dorso'),
]

class OtraCantidad(ModelSQL, ModelView):
    "Otra Cantidad"
    __name__ = 'sale_printery_budget.otra_cantidad'

    name = fields.Function(fields.Char('Name', size=None, translate=False),
                           'get_name')
    cantidad = fields.Integer('Cantidad', required=True)
    utilidad = fields.Integer('Porcentaje de Utilidad (%)', required=True)
    sale_id = fields.Many2One('sale.sale', 'Venta')
    total = fields.Function(fields.Numeric('Total', digits=(16, 2)),
                            'get_total_amount')
    contribucion_marginal = fields.Function(fields.Numeric('Contribucion \
                                                           marginal (%)',
                                                           digits=(16, 2)),
                                            'get_contribucion_marginal')

    @staticmethod
    def default_utilidad():
        return 0

    @classmethod
    def get_name(cls, otras_cantidades, name):
        res = {}
        for otra_cantidad in cls.browse(otras_cantidades):
            res[otra_cantidad.id] = otra_cantidad.cantidad

        return res

    @classmethod
    def get_contribucion_marginal(cls, otras_cantidades, name):
        res = {}
        for otra_cantidad in cls.browse(otras_cantidades):
            res[otra_cantidad.id] = \
                cls.calcular_contribucion_marginal(
                    otra_cantidad.sale_id, otra_cantidad.cantidad,
                    otra_cantidad.total)

        return res

    @classmethod
    def calcular_contribucion_marginal(cls, sale_id, cantidad, total):
        if total == 0:
            return Decimal('0.00')

        def es_ajeno(line):
            if line.product is None:
                return False

            Product = Pool().get('product.product')
            genera_contribucion_marginal = line.product.genera_contribucion_marginal

            if type(line.product) is not Product:
                return False

            if genera_contribucion_marginal:
                return False

            return True

        gastos_ajenos = cls._calcular_gastos(sale_id, cantidad, es_ajeno)
        contribucion = (total - gastos_ajenos) / total * 100
        return contribucion

    @classmethod
    def get_total_amount(cls, otras_cantidades, name):
        res = {}
        for otra_cantidad in cls.browse(otras_cantidades):
            sale = otra_cantidad.sale_id
            res[otra_cantidad.id] = cls.calcular_total(sale,
                                                       otra_cantidad.cantidad,
                                                       otra_cantidad.utilidad)
        return res

    @classmethod
    def _calcular_gastos(self, sale, cantidad, filtro):

        gasto_fijo = sum((line.amount
                          for line in sale.lines
                          if (line.type == 'line'
                              and filtro(line)
                              and line.fijo)), Decimal(0))
        gasto_variable = sum((line.amount
                              for line in sale.lines
                              if (line.type == 'line'
                                  and filtro(line)
                                  and not line.fijo)), Decimal(0))

        escala = Decimal(float(cantidad) / sale.cantidad)

        return gasto_fijo + gasto_variable * escala

    @classmethod
    def calcular_total(self, sale, cantidad, utilidad):
        Currency = Pool().get('currency.currency')
        gastos = self._calcular_gastos(sale, cantidad, lambda x: True)
        return Currency.round(sale.currency, gastos * (100 + utilidad) / 100)


class Sale:
    __metaclass__ = PoolMeta
    __name__ = 'sale.sale'

    cantidad = fields.Integer('Cantidad', required=True,
                states={
                    'readonly': Eval('state') != 'draft',
                }, depends=['state'])

    otra_cantidad = fields.One2Many('sale_printery_budget.otra_cantidad',
                    'sale_id',
                    'Otra Cantidad',
                    states={
                        'readonly': Eval('state') != 'draft',
                    }, depends=['state'])

    orden_trabajo = fields.One2Many('sale_printery_budget.orden_trabajo',
                    'sale',
                    'Orden Trabajo',
                    states={
                        'readonly': Eval('state') != 'draft',
                    }, depends=['state'])

    cantidad_confirmada = fields.Many2One('sale_printery_budget.otra_cantidad',
                            'Cantidad Confirmada',
                            domain=[('sale_id', '=', Eval('active_id', -1))],
                            states={
                                'invisible': Eval('state').in_(['draft', 'cancel']),
                                'readonly': Eval('state') != 'quotation',
                                'required': ~Eval('state').in_(['draft', 'quotation', 'cancel', 'expired']),
                            })

    state = fields.Selection([
        ('draft', 'Draft'),
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
        ('expired', 'Vencida'),
    ], 'State', readonly=True, required=True)
    sale_date = fields.Date('Sale Date',
        states={
            'readonly': ~Eval('state').in_(['draft', 'quotation']),
            'required': ~Eval('state').in_(['draft', 'quotation', 'cancel', 'expired']),
            },
        depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._error_messages.update({
            'miss_cantidad': 'Se debe setear la cantidad confirmada!',
            'miss_otras_cantidades': 'Se debe agregar al menos una cantidad en "Otras cantidades"',
        })
        cls._buttons.update({
                'calcular_papel': {
                    'invisible': ~Eval('state').in_(['draft']),
                    },
                'retomar_calcular_papel': {
                    'invisible': ~Eval('state').in_(['draft']),
                    },
        })

    @classmethod
    def vencimiento_trigger(self):
        ''' Cambia el estado a vencimiento de las ventas presupuestadas hace mas de 15 días '''
        Sale = Pool().get('sale.sale')

        # Chequear la function trigger_write.
        #http://doc.tryton.org/3.0/trytond/doc/ref/models/models.html#trytond.model.ModelStorage.trigger_write
        sales = Sale.search([('state', '=', 'quotation'), ('write_date', '<', datetime.datetime.now() - datetime.timedelta(days=15))])
        Sale.write([s['id'] for s in sales], {'state': 'expired'})

    @classmethod
    def view_attributes(cls):
        return super(Sale, cls).view_attributes() + [
            ('//page[@id="otra_cantidad"]', 'states', {
                    'invisible': ~Eval('state').in_(['draft', 'quotation']),
                    })]

    @classmethod
    @ModelView.button_action('sale_printery_budget.wizard_calcular_papel')
    def calcular_papel(cls, sales):
        pass

    @classmethod
    @ModelView.button_action('sale_printery_budget.wizard_retomar_calcular_papel')
    def retomar_calcular_papel(cls, sales):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('quotation')
    def quote(self, sales):
        for sale in sales:
            if not sale.otra_cantidad:
                self.raise_user_error('miss_otras_cantidades')

        super(Sale, self).quote(sales)

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(self, sales):
        pool = Pool()
        Sale = pool.get('sale.sale')
        SaleLine = pool.get('sale.line')
        OtraCantidad = pool.get('sale_printery_budget.otra_cantidad')
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')
        OrdenTrabajo = pool.get('sale_printery_budget.orden_trabajo')
        CalcularPapelProducto = pool.get('sale_printery_budget.calcular_papel.producto')
        for sale in sales:
            if not sale.cantidad_confirmada:
                self.raise_user_error('miss_cantidad')
            cantidad_vals = OtraCantidad.search_read([('id', '=', sale.cantidad_confirmada.id)], fields_names=['cantidad', 'utilidad'])[0]
            cantidad_confirmada = cantidad_vals['cantidad']
            utilidad = cantidad_vals['utilidad']

            utilidad_producto = Product.search([('product_type_printery', '=', \
                                    'utilidad')])[0]
            # Agregar línea utilidad
            sale_line = {
                    'sale': sale.id,
                    'sequence': 10,
                    'product': utilidad_producto.id,
                    'type': 'line',
                    'quantity': 1,
                    'unit': Uom.search_read([('id', '=', Id('product', 'uom_unit').pyson())],fields_names=['id'])[0]['id'],
                    'unit_price': Decimal(OtraCantidad._calcular_gastos(sale, cantidad_confirmada, lambda x: True) * utilidad / 100).quantize(Decimal('.01')),
                    'description': 'Utilidad (%d %%)' % utilidad,
                    'fijo': True,
                    }
            SaleLine.create([sale_line])

        # Actualizamos las lineas
        escala = float(cantidad_confirmada) / sale.cantidad
        line_ids = SaleLine.search([('sale', '=', sale.id)])
        interiores_ids = set()
        for line in SaleLine.browse(line_ids):
            if line.type == 'line' and not line.fijo:
                if line.unit_digits is 0:
                    unit_digits = '0'
                else:
                    unit_digits = '.01'
                SaleLine.write([line], {'quantity': Decimal(line.quantity * escala).quantize(Decimal(unit_digits))})

            if line.type == 'line' and line.id_interior is not None:
                interiores_ids.add(line.id_interior)

        SaleLine.write([sale], {'cantidad': cantidad_confirmada})
        # Paso a confirmado las ordenes de trabajo correspondientes.
        # Borrar ordenes de trabajo que no tienen linea de venta.
        # Actualizar ordenes de trabajo con la cantidad confirmada.
        for interior_id in interiores_ids:
            orden_trabajo = OrdenTrabajo.search([('id_interior', '=', interior_id), ('sale', '=', sale.id)])[0]
            # Actualizamos lineas:
            #- Pliegos Netos
            #- Cantidad de Planchas (V)
            #- Pliegos Demasia Variable (V)
            #- Pliegos Demasia Fija
            #- Cantidad
            #- Cantidad Confirmada
            #- Cantidad Hojas (V)
            #- Tiempo Impresión (agregar este campo) (V)
            #- Tiempo de arranque (agregar este campo) (F)
            #- Tinta (agregar este campo)
            update_line = {
                'state': 'confirmed',
                'cantidad_hojas': ceil(Decimal(orden_trabajo.cantidad_hojas * escala).quantize(Decimal('.01'))),
                'cantidad_confirmada': sale.cantidad_confirmada.id,
                'cantidad': sale.cantidad_confirmada.cantidad,
                'cantidad_planchas': ceil(Decimal(orden_trabajo.cantidad_planchas * escala).quantize(Decimal('.01'))),
                'pliegos_demasia_variable':ceil(Decimal(orden_trabajo.pliegos_demasia_variable * escala).quantize(Decimal('.01'))),
                'tiempo_impresion':Decimal(orden_trabajo.tiempo_impresion * Decimal(escala)).quantize(Decimal('.01')),
            }

            OrdenTrabajo.write([orden_trabajo], update_line)

        ordenes_trabajo = OrdenTrabajo.search([('sale', '=', sale.id), ('state', '=', 'draft')])
        OrdenTrabajo.delete(ordenes_trabajo)
        # Borro productos temporales asociados a la venta.
        productos_temporales = CalcularPapelProducto.search([('sale_id', '=', sale.id)])
        CalcularPapelProducto.delete(productos_temporales)

        super(Sale, self).confirm(sales)


class PresupuestoClienteReport(Report):
    __name__ = 'sale_printery_budget.presupuesto_cliente'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        User = pool.get('res.user')
        user = User(Transaction().user)
        report_context = super(PresupuestoClienteReport, cls).get_context(records, data)
        report_context['company'] = user.company
        return report_context


class SaleLine:
    __metaclass__ = PoolMeta
    __name__ = 'sale.line'

    fijo = fields.Boolean('Fijo',
                          states={'invisible': Eval('type') != 'line'},
                          depends=['type'])
    id_interior = fields.Char('id interior')


class CalcularPapelProducto(ModelSQL, ModelView):
    "Wizard Producto"
    __name__ = 'sale_printery_budget.calcular_papel.producto'

    name = fields.Char('Papel', size=None, translate=True,
                       select=True)
    producto = fields.Many2One('product.product', 'Producto',
                               select=True)
    orientacion_papel = fields.Selection([
        ('H', 'Horizontal'),
        ('V', 'Vertical'),
    ], u'Orientación Papel')

    orientacion_trabajo = fields.Selection([
        ('H', 'Horizontal'),
        ('V', 'Vertical'),
    ], u'Orientación Trabajo')
    ancho_pliego = fields.Float('Ancho Pliego', digits=(16, 2))
    alto_pliego = fields.Float('Alto Pliego', digits=(16, 2))
    pliegos_por_hoja = fields.Integer('Pliegos por Hoja')
    cantidad_de_pliegos = fields.Integer('Cantidad de Pliegos')
    trabajos_por_pliego = fields.Char('Trabajos por Pliego')

    cantidad_hojas = fields.Integer('Cantidad de Hojas')
    desperdicio = fields.Numeric('Desperdicio (%)', digits=(3, 0))
    # Auxiliar para filtrar los productos
    id_wizard = fields.Char('id del wizard')
    producto_id = fields.Integer('ID del producto')
    sale_id = fields.Integer('sale_id')

class CalcularPapelElegirInterior(ModelView):
    "Wizard Start"
    __name__ = 'sale_printery_budget.calcular_papel.elegir_interior'

    sale_id = fields.Integer('sale_id', readonly=True)
    orden_trabajo = fields.Many2One('sale_printery_budget.orden_trabajo',
                                    'Orden de Trabajo',
                                    domain=[('sale', '=', Eval('sale_id'))],
                                    required=True)


class CalcularPapelWizard(ModelView):
    "Wizard Start"
    __name__ = 'sale_printery_budget.calcular_papel.wizard'

    categoria = fields.Selection([
        ('revista_libro', 'Revista/Libro'),
        ('folleto', 'Folleto'),
        ('cuaderno', 'Cuaderno'),
    ], 'Categoria', required=True)
    altura = fields.Numeric('Altura', digits=(16, 2),
                            required=True)
    ancho = fields.Numeric('Ancho', digits=(16, 2),
                           required=True)
    es_tapa = fields.Boolean(u'¿Es tapa?', states={
        'invisible': Eval('categoria').in_(['folleto']),
    }, select=False,
        depends=['categoria'])
    sin_pinza = fields.Boolean(u'Sin Pinza', select=False)
    id_wizard_start = fields.Char('id de wizard', states={'invisible': True})
    sale_id = fields.Integer('sale_id', states={'invisible': True})
    producto_id = fields.Integer('id de producto', states={'invisible': True})
    cantidad = fields.Integer('Cantidad', required=True, states={'invisible': False})
    calle_horizontal = fields.Numeric(u'Calle Horizontal', digits=(16, 2), required=True)
    calle_vertical = fields.Numeric(u'Calle Vertical', digits=(16, 2), required=True)
    tipo_papel = fields.Many2One('product.category', u'Tipo de papel',
                                 domain=[('parent', '=', Id('sale_printery_budget',
                                                            'cat_papel'))],
                                 required=True)
    gramaje = fields.Numeric('Gramaje', digits=(16, 2), required=True)
    solapa = fields.Numeric('Solapa', digits=(16, 2), states={
        'invisible': Eval('categoria').in_(['folleto']),
    }, required=False,
        depends=['categoria'])
    lomo = fields.Numeric('Lomo', digits=(16, 2), states={
        'invisible': Not(Bool(Eval('es_tapa')))
    }, required=False,
        depends=['es_tapa'])
    cantidad_paginas = fields.Integer(u'Cantidad de Paginas', states={
        'invisible': Eval('categoria').in_(['folleto']),
    }, required=False,
        depends=['categoria'])
    # Datos superficiales
    colores_frente = fields.Integer(u'Colores Frente', required=True)
    colores_dorso = fields.Integer(u'Colores Dorso', required=True)
    doblado = fields.Many2One('product.product', u'Doblado',
                                        domain=[('template.product_type_printery', '=', 'maquina_doblado')],
                                        required=False)
    encuadernado = fields.Many2One('product.product', u'Encuadernado',
                                     domain=[('template.product_type_printery', '=', 'maquina_encuadernacion')],
                                     required=False,
                                     depends=['categoria'],
                                     states={
                                         'invisible': Eval('categoria').in_(['folleto']),
                                     })
    cantidad_broches = fields.Integer('Cantidad de Broches', states={
        'invisible': Eval('categoria').in_(['folleto']),
        'required': Bool(Eval('encuadernado')),
    }, depends=['categoria', 'encuadernado'])
    laminado = fields.Many2One('product.product', u'Laminado',
                                        domain=[('template.product_type_printery', '=', 'maquina_laminado')],
                                        required=False)
    laminado_orientacion = fields.Selection(ORIENTACION, 'Laminado Orientacion', states={
        'required': Bool(Eval('laminado')),
    }, depends=['laminado'])
    maquina = fields.Many2One('product.product', u'Máquina',
                              domain=[('template.product_type_printery', '=', 'maquina')],
                              required=True)
    producto_papel = fields.Many2One('sale_printery_budget.calcular_papel.producto',
                        u'Papel',
                        domain=[('id_wizard', '=', Eval('id_wizard_start'))],
                        required=True,
                        states={'readonly': False,})
    demasia_variable = fields.Integer('Demasia Variable(%)', required=True)
    demasia_fija = fields.Integer('Demasia Fija', required=True)
    tinta = fields.Many2One('product.product', u'Tinta',
                              domain=[('template.product_type_printery', '=', 'tinta')],
                              required=True)
    tinta_superficie_cubierta = fields.Integer('Tinta (superficie Cubierta(%))', required=True)
    velocidad_maquina = fields.Selection([
        ('tiempo_rapido', u'Tiempo Rápido'),
        ('tiempo_medio', u'Tiempo Medio'),
        ('tiempo_lento', u'Tiempo Lento'),
    ], 'Velocidad Maquina', required=True)
    # Campos readonly
    trabajos_por_pliego = fields.Char('Trabajos por Pliego', states={'readonly': True})
    formato_pliego = fields.Char('Formato Pliego', states={'readonly': True})
    cantidad_planchas = fields.Integer('Cantidad Planchas', states={'readonly': True})
    plancha_adicional = fields.Integer('Plancha Adicional', states={'readonly': False}, required=True)
    pliegos_netos = fields.Integer('Pliegos Netos', states={'readonly': True})
    postura_trabajo = fields.Selection([('H', 'Horizontal'),('V', 'Vertical')],
                               u'Postura Trabajo', states={'readonly': True})
    postura_papel = fields.Selection([('H', 'Horizontal'),('V', 'Vertical')],
                               u'Postura Papel', states={'readonly': True})
    @classmethod
    def __setup__(cls):
        super(CalcularPapelWizard, cls).__setup__()
        cls._error_messages.update({
            'cantidad_paginas_multiplo_de_dos': 'Cantidad de paginas debe ser multiplo de 2',
            'cantidad_paginas_multiplo_de_cuatro': 'Cantidad de paginas debe ser multiplo de 4',
        })

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_categoria(self):
        logger.info('on_change_categoria')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_cantidad_paginas(self):
        logger.info('on_change_cantidad_paginas')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_lomo(self):
        logger.info('on_change_lomo')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_es_tapa(self):
        logger.info('on_change_es_tapa')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_solapa(self):
        logger.info('on_change_solapa')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_altura(self):
        logger.info('on_change_altura')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_ancho(self):
        logger.info('on_change_ancho')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_tipo_papel(self):
        logger.info('on_change_gramaje')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_gramaje(self):
        logger.info('on_change_gramaje')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_maquina(self):
        logger.info('on_change_maquina')
        self._generate_producto_papel(self)
        try:
            if self.maquina.demasia_fija:
                self.demasia_fija = self.maquina.demasia_fija

            if self.maquina.demasia_variable:
                self.demasia_variable = self.maquina.demasia_variable
        except:
            logger.info('Variable indefinida')

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_cantidad(self):
        logger.info('on_change_cantidad')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_calle_horizontal(self):
        logger.info('on_change_calle_horizontal')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_calle_vertical(self):
        logger.info('on_change_calle_vertical')
        self._generate_producto_papel(self)

    @fields.depends('maquina', 'altura', 'ancho', 'tipo_papel', 'gramaje', 'id_wizard_start', 'cantidad', 'calle_horizontal', 'calle_vertical', 'sin_pinza', 'categoria', 'solapa', 'lomo', 'es_tapa', 'sale_id', 'cantidad_paginas')
    def on_change_sin_pinza(self):
        logger.info('on_change_sin_pinza')
        self._generate_producto_papel(self)

    @fields.depends('producto_papel', 'colores_frente', 'colores_dorso', 'cantidad_paginas', 'categoria')
    def on_change_with_cantidad_planchas(self, name=None):
        logger.info('on_change_with_cantidad_planchas')
        if self.producto_papel is None:
            return None

        cantidad_planchas = 0
        poses_alto = int(self.producto_papel.trabajos_por_pliego.split('x')[0])
        poses_ancho = int(self.producto_papel.trabajos_por_pliego.split('x')[1])

        if self.categoria == 'folleto' or self.categoria == 'cuaderno':
            if (poses_alto*poses_ancho) % 2 == 0:
                "print trabajos por pliego es par"
                cantidad_planchas = self.colores_frente
            else:
                "print trabajos por pliego es impar"
                cantidad_planchas = self.colores_frente + self.colores_dorso
        else:
            colores = self.colores_frente + self.colores_dorso
            cuenta_parcial = Decimal(self.cantidad_paginas) / Decimal(poses_alto*poses_ancho*4)
            if cuenta_parcial % 1 == Decimal('0'):
                return cuenta_parcial * colores
            if cuenta_parcial % 1 <= Decimal('0.5') and  cuenta_parcial % 1 > Decimal('0'):
                cuenta_parcial = int(cuenta_parcial) + Decimal('0.5')
                return cuenta_parcial * colores
            else:
                cuenta_parcial = int(cuenta_parcial) + Decimal('1')
                return cuenta_parcial * colores

        return cantidad_planchas

    @fields.depends('producto_papel')
    def on_change_with_postura_trabajo(self, name=None):
        logger.info('on_change_with_postura_trabajo')
        if self.producto_papel is None:
            return None

        return self.producto_papel.orientacion_trabajo

    @fields.depends('producto_papel')
    def on_change_with_postura_papel(self, name=None):
        logger.info('on_change_with_postura_papel')
        if self.producto_papel is None:
            return None

        return self.producto_papel.orientacion_papel

    @fields.depends('producto_papel')
    def on_change_with_pliegos_netos(self, name=None):
        logger.info('on_change_with_pliegos_netos')
        if self.producto_papel is None:
            return None

        return self.producto_papel.cantidad_de_pliegos

    @fields.depends('producto_papel')
    def on_change_with_trabajos_por_pliego(self, name=None):
        logger.info('on_change_with_formato_pliego')
        if self.producto_papel is None:
            return None

        return self.producto_papel.trabajos_por_pliego

    @fields.depends('producto_papel')
    def on_change_with_formato_pliego(self, name=None):
        logger.info('on_change_with_formato_pliego')
        if self.producto_papel is None:
            return None

        return str(self.producto_papel.ancho_pliego) + 'x' + str(self.producto_papel.alto_pliego)

    def _generate_producto_papel(self, values):
        if values.id_wizard_start:
            self._borrar_productos_temporales(values.id_wizard_start)
            self.producto_papel = None
            self.pliegos_netos = None
            self.trabajos_por_pliego = None
            self.formato_pliego = None
            self.cantidad_planchas = None
            self.plancha_adicional = 0
            self.postura_trabajo = None
            self.postura_papel = None

        self.id_wizard_start = '0'

        if values.categoria == 'cuaderno' and values.cantidad_paginas % 2 != 0:
            self.raise_user_error('cantidad_paginas_multiplo_de_dos')
        if values.categoria == 'revista_libro' and values.cantidad_paginas % 4 != 0:
            self.raise_user_error('cantidad_paginas_multiplo_de_cuatro')

        if values.ancho and values.altura and values.gramaje and values.maquina and values.tipo_papel and values.cantidad:
            id_wizard = str(uuid.uuid1())
            self.id_wizard_start = id_wizard
            Product = Pool().get('product.product')
            papeles = Product.search([('category', '=', values.tipo_papel),
                                              ('weight', '=', values.gramaje),
                                              ('product_type_printery', '=', 'papel')])

            values_tmp = values
            if values.categoria == 'cuaderno':
                # Las dimensiones no cambian. Cambia la cantidad a imprimir.
                values_tmp.cantidad = values_tmp.cantidad * values_tmp.cantidad_paginas // 2
            if values.categoria == 'revista_libro':
                values_tmp.cantidad = values_tmp.cantidad * values_tmp.cantidad_paginas // 4
                values_tmp.ancho = (values_tmp.ancho * 2) + values_tmp.calle_horizontal

            if values.categoria != 'folleto' and values_tmp.solapa is not None and \
                    values_tmp.solapa > 0 and values.es_tapa:
                values_tmp.ancho = values_tmp.ancho + values_tmp.solapa

            if values.categoria != 'folleto' and values_tmp.lomo is not None and values_tmp.lomo > 0:
                values_tmp.ancho = values_tmp.ancho + values_tmp.lomo

            for papel in papeles:
                tmp = {}
                tmp['id_wizard'] = id_wizard
                tmp['producto_id'] = papel.id
                tmp['name'] = papel.name
                for orientacion_papel in ['H', 'V']:
                    tmp['orientacion_papel'] = orientacion_papel
                    self._agregar_datos_y_crear_producto_papel(tmp, values_tmp)

    def _borrar_productos_temporales(self, id_wizard_start='0'):
        CalcularPapelProducto = Pool().get('sale_printery_budget.calcular_papel.producto')
        productos_a_borrar = CalcularPapelProducto.search([('id_wizard', '=',
                                                       id_wizard_start)])
        with Transaction().new_transaction() as transaction:
            CalcularPapelProducto.delete(productos_a_borrar)
            transaction.commit()

    def _agregar_datos_y_crear_producto_papel(self, tmp, values):
        """ Recibe papel, tamaño del producto, y maquina """
        # Repetir a lo que yo imprimo hasta la mínima dimension que
        # tiene entra en la maquina. (formato max. maquina).
        # Por cada repetición, evaluar si el pliego mínimo puede ser usado o
        # no. Si se usa, se agrega al tmp de productos a mostrar.

        pool = Pool()
        Product = pool.get('product.product')
        CalcularPapelProducto = pool.get('sale_printery_budget.calcular_papel.producto')
        papel_producto = Product.search([('id', '=', tmp['producto_id'])])[0]
        #UOM
        #uom_obj = pool.get('product.uom')
        #maquina_uom = uom_obj.search([('id', '=',  values.maquina.maquina_uom.id)])[0]
        #height_uom = uom_obj.search([('id', '=',  papel_producto.height_uom.id)])[0]
        #width_uom = uom_obj.search([('id', '=',  papel_producto.width_uom.id)])[0]
        #uom_to = uom_obj.search([('symbol', '=','cm')])[0]
        # Se debe pasar todos los números a centimetros.
        #papel_producto_height = uom_obj.compute_price(height_uom, Decimal(papel_producto.height), uom_to).quantize(Decimal('.01'))
        #papel_producto_width = uom_obj.compute_price(width_uom, Decimal(papel_producto.width), uom_to).quantize(Decimal('.01'))
        #maquina_width_max = uom_obj.compute_price(width_uom, Decimal(papel_producto.width), uom_to)
        #maquina_height_max = uom_obj.compute_price(width_uom, Decimal(papel_producto.width), uom_to)

        area_hoja = Decimal(papel_producto.height) * Decimal(papel_producto.width)
        calle_horizontal = Decimal(values.calle_horizontal)
        calle_vertical = Decimal(values.calle_vertical)
        sin_pinza = values.sin_pinza
        sale_id = values.sale_id

        if tmp['orientacion_papel'] == 'H':
            ancho_papel = papel_producto.height
            alto_papel = papel_producto.width
        else:
            ancho_papel = papel_producto.width
            alto_papel = papel_producto.height

        if values.maquina.width_max < ancho_papel:
            ancho_maximo = values.maquina.width_max
        else:
            ancho_maximo = ancho_papel

        if values.maquina.height_max < alto_papel:
            alto_maximo = values.maquina.height_max
        else:
            alto_maximo = alto_papel

        for orientacion_trabajo in ['H', 'V']:
            papel = tmp
            if orientacion_trabajo == 'H':
                ancho = values.altura
                altura = values.ancho
            else:
                ancho = values.ancho
                altura = values.altura

            ancho_de_trabajo = Decimal(values.maquina.laterales)
            poses_ancho = 0
            while ancho_de_trabajo <= ancho_maximo:
                poses_ancho = poses_ancho + 1
                ancho_de_trabajo = ancho_de_trabajo + ancho

                if poses_ancho > 1:
                    ancho_de_trabajo = ancho_de_trabajo + calle_horizontal

                if ancho_de_trabajo >= values.maquina.width_min and ancho_de_trabajo <= ancho_maximo:

                    # Por lo menos tenemos un folleto. Ahora verificamos
                    # cuantos van en vertical.
                    if sin_pinza:
                        alto_de_trabajo = Decimal(0)
                    else:
                        alto_de_trabajo = Decimal(values.maquina.pinza + values.maquina.cola)

                    poses_alto = 0
                    while alto_de_trabajo <= alto_maximo:

                        poses_alto = poses_alto + 1
                        alto_de_trabajo = alto_de_trabajo + altura

                        if poses_alto > 1:
                            alto_de_trabajo = alto_de_trabajo + calle_vertical

                        if alto_de_trabajo >= values.maquina.height_min and alto_de_trabajo <= alto_maximo:
                            # Por último, si es usado, se hacen los cálculos de pliegos por hoja,
                            # etc
                            pliegos_por_hoja = (Decimal(alto_papel) // alto_de_trabajo) * \
                                (Decimal(ancho_papel) // ancho_de_trabajo)
                            papel['ancho_pliego'] = ancho_de_trabajo
                            papel['alto_pliego'] = alto_de_trabajo
                            area_pliego_producto = ancho_de_trabajo * alto_de_trabajo
                            papel['pliegos_por_hoja'] = pliegos_por_hoja
                            papel['desperdicio'] = Decimal((area_hoja - pliegos_por_hoja * area_pliego_producto) / area_hoja * 100).quantize(0)
                            papel['cantidad_de_pliegos'] = Decimal(ceil(values.cantidad / (poses_alto * poses_ancho)))
                            papel['cantidad_hojas'] = Decimal(ceil(papel['cantidad_de_pliegos'] / pliegos_por_hoja))
                            papel['trabajos_por_pliego'] = str(poses_alto) + 'x' + str(poses_ancho)
                            papel['orientacion_trabajo'] = orientacion_trabajo
                            papel['producto_id'] = papel['producto_id']
                            papel['sale_id'] = sale_id

                            with Transaction().new_transaction() as transaction:
                                CalcularPapelProducto.create([papel])
                                transaction.commit()


class CalcularPapel(Wizard):
    "Wizard Calcular Papel"
    __name__ = 'sale_printery_budget.calcular_papel'
    start_state = 'interior'
    interior = StateView('sale_printery_budget.calcular_papel.wizard',
                                 'sale_printery_budget.calcular_papel_interior_view_form', [
                                     Button('Cancelar', 'end', 'tryton-cancel'),
                                     Button('Siguiente Interior', 'interior', 'tryton-go-next'),
                                     Button('Terminar', 'terminar', 'tryton-ok', True),
                                 ])

    terminar = StateTransition()

    def default_interior(self, fields):
        "Crear las lineas de producto en la venta"
        logger.info('default_interior')
        ## Desde aca puedo crear las lineas de los productos.
        # Primero preguntar si cls.interior.producto_papel es distinto de None.
        # Si es asi, entonces cargo las lineas.
        t = Transaction()
        Sale = Pool().get('sale.sale')
        ut = utils()
        ut.interior = self.interior
        sale = Sale.search([('id', '=', t.context['active_id'])])[0]
        res = {
            'categoria': 'folleto',
            'calle_horizontal': Decimal('0.5'),
            'calle_vertical': Decimal('0.5'),
            'colores_frente': 0,
            'colores_dorso': 0,
            'plancha_adicional': 0,
            'cantidad_paginas': 4,
            'cantidad': sale.cantidad,
            'sale_id': sale.id,
        }

        if hasattr(self.interior, 'producto_papel') == False or self.interior.producto_papel is None:
            # Primera vez que se ejecuta la pantalla interior.
            try:
                ut.borrar_productos_temporales(self.interior.id_wizard_start)
            except:
                logger.info('Primera vez que se ejecuta la pantalla. No se pudo borrar productos temporales')

            return res

        lineas_venta = ut.creo_lineas_de_venta()
        ut.creo_orden_trabajo(sale, lineas_venta)
        ut.crear_otra_cantidad_base(sale)
        ut.borrar_productos_temporales(self.interior.id_wizard_start)
        return res

    def transition_terminar(self):
        "Crear las lineas de producto en la venta y finalizar wizard"
        logger.info('Borrar lineas del producto temporal al Finalizar Wizard')

        t = Transaction()
        Sale = Pool().get('sale.sale')
        sale = Sale.search([('id', '=', t.context['active_id'])])[0]
        ut = utils()
        ut.interior = self.interior

        if hasattr(self.interior, 'producto_papel') == False or self.interior.producto_papel is None:
            # Primera vez que se ejecuta la pantalla interior.
            try:
                ut.borrar_productos_temporales(self.interior.id_wizard_start)
            except:
                logger.info('Primera vez que se ejecuta la pantalla. No se pudo borrar productos temporales')

            # Debo verificar que la venta ya tiene lineas de venta. Si es así,
            # calcular otras cantidades y return 'end'.
            if sale.lines:
                ut.crear_otra_cantidad_base(sale)
            return 'end'

        lineas_venta = ut.creo_lineas_de_venta()
        ut.creo_orden_trabajo(sale, lineas_venta)
        ut.crear_otra_cantidad_base(sale)
        ut.borrar_productos_temporales(self.interior.id_wizard_start)
        return 'end'


class RetomarCalcularPapel(Wizard):
    "Wizard Retomar Calcular Papel"
    __name__ = 'sale_printery_budget.retomar_calcular_papel'
    start_state = 'elegir_interior'

    elegir_interior = StateView('sale_printery_budget.calcular_papel.elegir_interior',
                                 'sale_printery_budget.calcular_papel_elegir_interior_view_form', [
                                     Button('Cancelar', 'end', 'tryton-cancel'),
                                     Button('Siguiente', 'interior', 'tryton-go-next', True),
                                 ])
    interior = StateView('sale_printery_budget.calcular_papel.wizard',
                                 'sale_printery_budget.calcular_papel_interior_view_form', [
                                     Button('Cancelar', 'end', 'tryton-cancel'),
                                     Button('Terminar', 'terminar', 'tryton-ok', True),
                                 ])

    terminar = StateTransition()

    def default_elegir_interior(self, fields):
        "Elegir que orden de trabajo retoma el wizard"
        logger.info('default_elegir_interior')
        t = Transaction()
        res = {
            'sale_id': t.context['active_id'],
        }
        return res

    def default_interior(self, fields):
        "Crear las lineas de producto en la venta"
        logger.info('default_retomar_calcular_papel_interior')
        pool = Pool()
        ut = utils()
        OrdenTrabajo = pool.get('sale_printery_budget.orden_trabajo')
        interior = OrdenTrabajo.search([('id', '=', self.elegir_interior.orden_trabajo.id)])[0]
        # Borrar producto temporal anterior
        ut.interior = interior
        ut.borrar_productos_temporales(interior.id_interior)

        # Copiar la orden de trabajo en modelo interior
        res = {
                'cantidad': interior.cantidad,
                'sale_id': interior.sale.id,
                'calle_horizontal': interior.calle_horizontal,
                'calle_vertical': interior.calle_vertical,
                'cantidad': interior.cantidad,
                'colores_frente': interior.colores_frente,
                'colores_dorso': interior.colores_dorso,
                'es_tapa': interior.es_tapa,
                'tipo_papel': interior.tipo_papel.id,
                'sin_pinza': interior.sin_pinza,
                'formato_pliego': interior.formato_pliego,
                'categoria': interior.categoria,
                'ancho': interior.ancho,
                'altura': interior.altura,
                'postura_papel': interior.postura_papel,
                'postura_trabajo': interior.postura_trabajo,
                #'maquina': interior.maquina.id,
                'tinta_superficie_cubierta': interior.tinta_superficie_cubierta,
                'tinta': interior.tinta.id,
                'solapa': interior.solapa,
                'lomo': interior.lomo,
                'gramaje': interior.gramaje,
                'id_wizard_start': interior.id_interior,
                'velocidad_maquina': interior.velocidad_maquina,
                'plancha_adicional': 0,
                'cantidad_paginas': interior.cantidad_paginas,
            }

        if hasattr(interior, 'doblado') != False and interior.doblado is not None:
            res['doblado'] = interior.doblado.id

        if hasattr(interior, 'encuadernado') != False and interior.encuadernado is not None:
            res['encuadernado'] = interior.encuadernado.id
            res['cantidad_broches'] = interior.cantidad_broches

        if hasattr(interior, 'laminado') != False and interior.laminado is not None:
            res['laminado'] = interior.laminado.id
            res['laminado_orientacion'] = interior.laminado_orientacion

        return res

    def transition_terminar(self):
        "Crear las lineas de producto en la venta y finalizar wizard"
        logger.info('Borrar lineas del producto temporal al Finalizar Wizard')

        pool = Pool()
        t = Transaction()
        ut = utils()
        Sale = pool.get('sale.sale')
        sale = Sale.search([('id', '=', t.context['active_id'])])[0]
        OrdenTrabajo = pool.get('sale_printery_budget.orden_trabajo')
        SaleLine = pool.get('sale.line')
        interior = OrdenTrabajo.search([('id', '=', self.elegir_interior.orden_trabajo.id)])[0]
        sale_lines = SaleLine.search(['id_interior', '=', interior.id_interior])
        # Borrar lineas anteriores y orden de trabajo anterior
        SaleLine.delete(sale_lines)
        OrdenTrabajo.delete([interior])

        # Genero lineas nuevas.
        ut.interior = self.interior
        lineas_venta = ut.creo_lineas_de_venta()
        ut.creo_orden_trabajo(sale, lineas_venta)
        ut.crear_otra_cantidad_base(sale)
        ut.borrar_productos_temporales(self.interior.id_wizard_start)

        return 'end'
