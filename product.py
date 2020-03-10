# This file is part sale_printery_budget module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pyson import Eval, Equal, Bool, Id, Not
from trytond.pool import PoolMeta

__all__ = ['Template']

STATES = {
    'readonly': ~Eval('active', True),
    }
DEPENDS = ['active']
TYPES_PRINTERY = [
    (None, ''),
    ('broche', 'Broche'),
    ('caja', 'Caja'),
    ('papel', 'Papel'),
    ('papel_rotativa', 'Papel Rotativa'),
    ('pallet', 'Pallet'),
    ('maquina', 'Maquina'),
    ('maquina_doblado', 'Maquina Doblado'),
    ('maquina_encuadernacion', 'Maquina Encuadernacion'),
    ('maquina_laminado', 'Maquina Laminado'),
    ('material_laminado', 'Material Laminado'),
    ('plancha', 'Plancha'),
    ('tinta', 'Tinta'),
    ('termocontraible', 'Termocontraible'),
    ('utilidad', 'Utilidad'),
    ('otros', 'Otros'),
    ]


class Template(metaclass=PoolMeta):
    __name__ = "product.template"
    product_type_printery = fields.Selection(TYPES_PRINTERY, 'Product Types',
        required=True, states=STATES, depends=DEPENDS)
    genera_contribucion_marginal = fields.Boolean('Contribución Marginal',
        select=False)
    cambio_de_plancha = fields.Integer('Cambio de Plancha',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    cambio_de_plancha_uom = fields.Many2One('product.uom',
        'Cambio de Plancha Uom',
        domain=[('category', '=', Id('product', 'uom_cat_time'))],
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            'required': Bool(Eval('cambio_de_plancha')),
            }, depends=['cambio_de_plancha', 'product_type_printery'])
    preparacion = fields.Integer('Preparación (por cada color)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    preparacion_uom = fields.Many2One('product.uom', 'Preparación Uom',
        domain=[('category', '=', Id('product', 'uom_cat_time'))],
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            'required': Bool(Eval('cambio_de_plancha')),
            }, depends=['cambio_de_plancha', 'product_type_printery'])
    tiempo_rapido = fields.Integer('Impresiones por hora (Rápido)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    tiempo_medio = fields.Integer('Impresiones por hora (Medio)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    tiempo_lento = fields.Integer('Impresiones por hora (Lento)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    plancha = fields.Many2One('product.product', 'Plancha',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            },
        domain=[
            ('template.product_type_printery', '=', 'plancha'),
            ],
        depends=['product_type_printery'])
    width_max = fields.Float('Ancho Máximo', digits=(16,
            Eval('width_digits', 2)), depends=['width_digits'])
    width_min = fields.Float('Ancho Mínimo', digits=(16,
            Eval('width_digits', 2)), depends=['width_digits'])
    height_max = fields.Float('Alto Máximo', digits=(16,
            Eval('height_digits', 2)), depends=['height_digits'])
    height_min = fields.Float('Alto Mínimo', digits=(16,
            Eval('height_digits', 2)), depends=['height_digits'])
    colores = fields.Integer('Colores Pasada',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            }, depends=['product_type_printery'])
    pinza = fields.Float('Pinza', digits=(16, 2),
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            }, depends=['product_type_printery'])
    cola = fields.Float('Cola', digits=(16, 2),
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            }, depends=['product_type_printery'])
    laterales = fields.Float('Laterales', digits=(16, 2),
        states={
            'invisible': Not(Eval('product_type_printery').in_(['maquina'])),
            }, depends=['product_type_printery'])
    maquina_uom = fields.Many2One('product.uom', 'Maquina Uom',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina')),
            },
        domain=[('category', '=', Id('product', 'uom_cat_length'))],
        depends=['product_type_printery'])
    velocidad_maq = fields.Numeric('Velocidad (metros / hora)', digits=(16, 2),
        states={
            'invisible': ~Eval('product_type_printery').in_(
                ['maquina_laminado', 'maquina_encuadernacion',
                    'maquina_doblado']),
            'required': Eval('product_type_printery').in_(
                ['maquina_laminado', 'maquina_encuadernacion',
                    'maquina_doblado']),
            }, depends=['product_type_printery'])
    tiempo_arreglo = fields.Numeric('Tiempo de arreglo (hs)', digits=(16, 2),
        states={
            'invisible': ~Eval('product_type_printery').in_(
                ['maquina_laminado', 'maquina_encuadernacion']),
            'required': Eval('product_type_printery').in_(
                ['maquina_laminado', 'maquina_encuadernacion']),
            }, depends=['product_type_printery'])
    broche = fields.Many2One('product.product', 'Broche',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'),
                    'maquina_encuadernacion')),
            'required': Equal(Eval('product_type_printery'),
                'maquina_encuadernacion'),
            },
        domain=[
            ('template.product_type_printery', '=', 'broche'),
            ],
        depends=['product_type_printery'])
    material_laminado = fields.Many2One('product.product', 'Material Laminado',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'),
                    'maquina_laminado')),
            'required': Equal(Eval('product_type_printery'),
                'maquina_laminado'),
            }, depends=['product_type_printery'],
        domain=[
            ('template.product_type_printery', '=', 'material_laminado'),
            ],
        required=False)
    # Plancha
    pliegos_por_plancha = fields.Integer('Pliegos por Plancha',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'plancha'))
            }, depends=['product_type_printery'])
    rendimiento_tinta = fields.Integer('Rendimiento de Tinta (gr/m2)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'tinta')),
            'required': Eval('product_type_printery').in_(['tinta']),
            }, depends=['product_type_printery'])
    demasia_fija = fields.Integer('Demasia Fija',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])
    demasia_variable = fields.Integer('Demasia Variable (%)',
        states={
            'invisible': Not(Equal(Eval('product_type_printery'), 'maquina'))
            }, depends=['product_type_printery'])

    @staticmethod
    def default_product_type_printery():
        return 'papel'

    @classmethod
    def view_attributes(cls):
        return super(Template, cls).view_attributes() + [
            ('//page[@id="mediciones_maquina"]', 'states', {
                    'invisible': Not(Eval('product_type_printery').in_(
                            ['maquina'])),
                    }),
            ('//page[@id="terminacion_superficial"]', 'states', {
                    'invisible': Not(Eval('product_type_printery').in_(
                            ['maquina_doblado', 'maquina_laminado',
                                'maquina_encuadernacion'])),
                    })
            ]

    # @fields.depends('product_type_printery')
    # def on_change_product_type_printery(self, name=None):
    #     if self.product_type_printery == 'papel':
    #         self.use_info_unit = True
