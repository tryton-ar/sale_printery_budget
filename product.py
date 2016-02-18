# -*- coding: utf-8 -*-
#This file is part sale_printery_budget module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval, Equal, Bool, Or, Id, Not
#from trytond.pool import Pool

_all__ = ['Template']

STATES = {
    'readonly': ~Eval('active', True),
    }
DEPENDS = ['active']
TYPES_PRINTERY = [
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

class Template(ModelSQL, ModelView):
    "Product Template"
    __name__ = "product.template"

    product_type_printery = fields.Selection(TYPES_PRINTERY, 'Product Types', required=True, states=STATES,depends=DEPENDS)
    genera_contribucion_marginal = fields.Boolean(u'Genera Contribución Marginal', select=False)
    cambio_de_plancha = fields.Integer('Cambio de Plancha',
                                       states={
                                           'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                       })
    cambio_de_plancha_uom = fields.Many2One('product.uom', 'Cambio de Plancha Uom',
                                            domain=[('category', '=', Id('product', 'uom_cat_time'))],
                                            states={
                                                'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                                                'required': Bool(Eval('cambio_de_plancha')),
                                            },
                                            depends=['cambio_de_plancha'])

    preparacion = fields.Integer(u'Preparación (por cada color)',
                                 states={
                                     'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                 })

    preparacion_uom = fields.Many2One('product.uom', u'Preparación Uom',
                                      domain=[('category', '=', Id('product', 'uom_cat_time'))],
                                      states={
                                          'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                                          'required': Bool(Eval('cambio_de_plancha')),
                                      },
                                      depends=['cambio_de_plancha'])

    tiempo_rapido = fields.Integer(u'Impresiones por hora (Rápido)',
                                   states={
                                       'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                   })

    tiempo_medio = fields.Integer(u'Impresiones por hora (Medio)',
                                  states={
                                      'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                  })

    tiempo_lento = fields.Integer(u'Impresiones por hora (Lento)',
                                  states={
                                      'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                  })

    plancha = fields.Many2One('product.product', u'Plancha',
                              states={
                                  'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                              },
                              domain=[('product_type_printery', '=', 'plancha')],
                              required=False)

    width_max = fields.Float(u'Ancho Máximo',
                             digits=(16, Eval('width_digits', 2)),
                             states={
                             #    'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                             })
    width_min = fields.Float(u'Ancho Mínimo',
                             digits=(16, Eval('width_digits', 2)),
                             states={
                             #    'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                             })
    height_max = fields.Float(u'Alto Máximo',
                              digits=(16, Eval('height_digits', 2)),
                              states={
                              #    'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                              })
    height_min = fields.Float(u'Alto Mínimo',
                              digits=(16, Eval('height_digits', 2)),
                              states={
                              #    'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                              })

    #Pinza, cola y Laterales (en cm).
    colores = fields.Integer('Colores Pasada',
                             states={
                                 'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                             })
    pinza = fields.Float('Pinza', digits=(16, 2),
                         states={
                             'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                         })
    cola = fields.Float('Cola', digits=(16, 2),
                        states={
                            'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                        })
    laterales = fields.Float('Laterales', digits=(16, 2),
                             states={
                                 'invisible':  Not(Eval('product_type_printery').in_(['maquina'])),
                             })
    maquina_uom = fields.Many2One('product.uom', 'Maquina Uom',
                                  states={
                                      'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina')),
                                  },
                                  domain=[('category', '=', Id('product', 'uom_cat_length'))],
                                  depends=['pinza', 'cola', 'laterales'])

    velocidad_maq = fields.Numeric('Velocidad (metros / hora)', digits=(16, 2))
    tiempo_arreglo = fields.Numeric('Tiempo de arreglo (hs)', digits=(16, 2))
    broche = fields.Many2One('product.product', u'Broche',
                              states={
                                  'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina_encuadernacion'))
                              },
                              domain=[('product_type_printery', '=', 'broche')],
                              required=False)
    material_laminado = fields.Many2One('product.product', u'Material Laminado',
                              states={
                                  'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina_laminado'))
                              },
                              domain=[('product_type_printery', '=', 'material_laminado')],
                              required=False)
    # Plancha
    pliegos_por_plancha = fields.Integer(u'Pliegos por Plancha',
                                 states={
                                     'invisible':  Not(Equal(Eval('product_type_printery'), 'plancha'))
                                 })
    rendimiento_tinta = fields.Integer(u'Rendimiento de Tinta (gr/m2)',
                                 states={
                                     'invisible':  Not(Equal(Eval('product_type_printery'), 'tinta'))
                                 })
    demasia_fija = fields.Integer(u'Demasia Fija',
                                 states={
                                     'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                 })
    demasia_variable = fields.Integer(u'Demasia Variable (%)',
                                 states={
                                     'invisible':  Not(Equal(Eval('product_type_printery'), 'maquina'))
                                 })

    @fields.depends('product_type_printery')
    def on_change_product_type_printery(self, name=None):
        res = {}
        if self.product_type_printery == 'papel':
            res = {
                'use_info_unit': True
            }
        return res
