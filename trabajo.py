# coding=utf-8
#This file is part of the sale_printery_budget module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields, Workflow
#from trytond.transaction import Transaction
from trytond.pyson import Id
from trytond.pyson import Eval
from trytond.report import Report
import logging
logger = logging.getLogger(__name__)

_all__ = ['OrdenTrabajo', 'OrdenTrabajoReport']

ORIENTACION = [
    ('', ''),
    ('frente', 'Frente'),
    ('dorso', 'Dorso'),
    ('frente_dorso', 'Frente/Dorso'),
]

class OrdenTrabajo(Workflow, ModelSQL, ModelView):
    "Ordenes de Trabajo"
    __name__ = 'sale_printery_budget.orden_trabajo'

    name = fields.Function(fields.Char('Name'), 'get_name')
    id_interior = fields.Char('id interior', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('process', 'Processing'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], 'State', readonly=True)
    cantidad_confirmada = fields.Many2One('sale_printery_budget.otra_cantidad',
        'Cantidad Confirmada',
        states={
            'readonly': True,
        })
    cantidad = fields.Integer('Cantidad', readonly=True)
    sale = fields.Many2One('sale.sale', 'Sale')
    categoria = fields.Selection([
        ('revista_libro', 'Revista/Libro'),
        ('folleto', 'Folleto'),
        ('cuaderno', 'Cuaderno'),
    ], 'Categoria', readonly=True)
    altura = fields.Numeric('Altura', digits=(16, 2),
                            readonly=True)
    ancho = fields.Numeric('Ancho', digits=(16, 2),
                           readonly=True)
    es_tapa = fields.Boolean(u'¿Es tapa?', readonly=True)
    calle_horizontal = fields.Numeric(u'Calle Horizontal', digits=(16, 2), readonly=True)
    calle_vertical = fields.Numeric(u'Calle Vertical', digits=(16, 2), readonly=True)
    sin_pinza = fields.Boolean(u'Sin Pinza', readonly=True)
    producto_papel = fields.Many2One('product.product', 'Papel', select=True, readonly=True)
    tipo_papel = fields.Many2One('product.category', u'Tipo de papel',
                                 domain=[('parent', '=', Id('sale_printery_budget', 'cat_papel'))], readonly=True)
    maquina = fields.Many2One('product.product', u'Máquina',
                              domain=[('product_type_printery', '=', 'maquina')], readonly=True)
    tinta = fields.Many2One('product.product', u'Tinta',
                              domain=[('product_type_printery', '=', 'tinta')], readonly=True)
    tinta_superficie_cubierta = fields.Integer('Tinta (superficie Cubierta(%))', readonly=True)
    colores_frente = fields.Integer(u'Colores Frente', readonly=True)
    colores_dorso = fields.Integer(u'Colores Dorso', readonly=True)
    ancho_pliego = fields.Float('Ancho Pliego', digits=(16, 2), readonly=True)
    alto_pliego = fields.Float('Alto Pliego', digits=(16, 2), readonly=True)
    pliegos_netos = fields.Integer('Pliegos Netos', readonly=True)
    cantidad_hojas = fields.Integer('Cantidad de Hojas', readonly=True)
    desperdicio = fields.Numeric('Desperdicio (%)', digits=(3, 0), readonly=True)
    trabajos_por_pliego = fields.Char('Trabajos por Pliego', states={'readonly': True})
    formato_pliego = fields.Char('Formato Pliego', states={'readonly': True})
    cantidad_planchas = fields.Integer('Cantidad Planchas', states={'readonly': True})
    postura_trabajo = fields.Selection([('H', 'Horizontal'),('V', 'Vertical')],
                               u'Postura Trabajo', states={'readonly': True})
    postura_papel = fields.Selection([('H', 'Horizontal'),('V', 'Vertical')],
                               u'Postura Papel', states={'readonly': True})
    velocidad_maquina = fields.Selection([
        ('tiempo_rapido', u'Tiempo Rápido'),
        ('tiempo_medio', u'Tiempo Medio'),
        ('tiempo_lento', u'Tiempo Lento'),
    ], 'Velocidad Maquina', readonly=True)
    solapa = fields.Numeric('Solapa', digits=(16, 2), readonly=True)
    lomo = fields.Numeric('Lomo', digits=(16, 2), readonly=True)
    cantidad_paginas = fields.Integer(u'Cantidad de Paginas', readonly=True)
    gramaje = fields.Numeric('Gramaje', digits=(16, 2), readonly=True)

    pliegos_demasia_fija = fields.Integer('Pliegos Demasia Fija', readonly=True)
    pliegos_demasia_variable = fields.Integer('Pliegos Demasia Variable', readonly=True)
    tiempo_arranque = fields.Numeric('Tiempo de Arranque', digits=(16,2), readonly=True)
    tiempo_impresion = fields.Numeric('Tiempo de Impresion', digits=(16,2), readonly=True)
    cantidad_tinta = fields.Numeric('Cantidad de Tinta', digits=(16,2), readonly=True)
    doblado = fields.Many2One('product.product', u'Doblado', readonly=True)
    encuadernado = fields.Many2One('product.product', u'Encuadernado', readonly=True)
    cantidad_broches = fields.Integer('Cantidad de Broches', readonly=True)
    laminado = fields.Many2One('product.product', u'Laminado', readonly=True)
    laminado_orientacion = fields.Selection(ORIENTACION, 'Laminado Orientacion', readonly=True)
    observaciones = fields.Text('Observaciones', size=None, required=False)

    @staticmethod
    def default_state():
        return "draft"

    @classmethod
    def get_name(cls, ordenes_trabajo, name):
        res = {}
        for orden_trabajo in cls.browse(ordenes_trabajo):
            res[orden_trabajo.id] = dict(orden_trabajo.fields_get(fields_names=['categoria'])\
            ['categoria']['selection'])[orden_trabajo.categoria] + ' ' +\
            str(orden_trabajo.ancho)+'x'+ str(orden_trabajo.altura)
        return res

    @classmethod
    def __setup__(cls):
        super(OrdenTrabajo, cls).__setup__()
        cls._transitions |= set((
                ('draft', 'confirmed'),
                ('confirmed', 'process'),
                ('confirmed', 'cancel'),
                ('cancel', 'draft'),
                ('cancel', 'confirmed'),
                ('process', 'confirmed'),
                ('process', 'done'),
                ))
        cls._buttons.update({
                'draft': {
                    'invisible': True,
                    },
                'confirmed': {
                    'invisible': ~Eval('state').in_(['process', 'cancel']),
                    },
                'process': {
                    'invisible': ~Eval('state').in_(['confirmed']),
                    },
                'done': {
                    'invisible': ~Eval('state').in_(['process']),
                    },
                'cancel': {
                    'invisible': ~Eval('state').in_(['confirmed']),
                    },
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirmed(cls, ordenes_trabajo):
        logger.info('Call def confirmed')
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('process')
    def process(cls, ordenes_trabajo):
        logger.info('Call def process')
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def done(cls, ordenes_trabajo):
        logger.info('Call def done')
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('cancel')
    def cancel(cls, ordenes_trabajo):
        logger.info('Call def cancel')
        pass


class OrdenTrabajoReport(Report):
    __name__ = 'sale_printery_budget.orden_trabajo'
