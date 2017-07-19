# coding=utf-8
#This file is part of the sale_printery_budget module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.

from decimal import Decimal
#import datetime
#import uuid
from math import ceil
from trytond.pool import Pool
#from trytond.pyson import Eval, Id, Bool, Not
from trytond.transaction import Transaction
import logging
logger = logging.getLogger(__name__)

class utils():

    interior = {}

    def test(self):
        logger.info(u'testeando: %s', str(self.interior.calle_horizontal))

    def creo_orden_trabajo(self, sale, lineas_venta):
        "Crear orden de trabajo basado en el papel elegido"
        logger.info('Creo orden de trabajo')
        pool = Pool()
        t = Transaction()
        orden_trabajo_line = {}
        OrdenTrabajo = pool.get('sale_printery_budget.orden_trabajo')
        orden_trabajo_line = {
                'sale':  t.context.get('active_id'),
                'state': 'draft',
                'calle_horizontal': self.interior.calle_horizontal,
                'calle_vertical': self.interior.calle_vertical,
                'cantidad': self.interior.cantidad,
                'colores_frente': self.interior.colores_frente,
                'colores_dorso': self.interior.colores_dorso,
                'es_tapa': self.interior.es_tapa,
                'tipo_papel': self.interior.tipo_papel.id,
                'producto_papel': self.interior.producto_papel.producto_id,
                'sin_pinza': self.interior.sin_pinza,
                'formato_pliego': self.interior.formato_pliego,
                'categoria': self.interior.categoria,
                'ancho': self.interior.ancho,
                'altura': self.interior.altura,
                'postura_papel': self.interior.postura_papel,
                'postura_trabajo': self.interior.postura_trabajo,
                'maquina': self.interior.maquina.id,
                'tinta_superficie_cubierta': self.interior.tinta_superficie_cubierta,
                'tinta': self.interior.tinta.id,
                'solapa': self.interior.solapa,
                'lomo': self.interior.lomo,
                'gramaje': self.interior.gramaje,
                'id_interior': self.interior.id_wizard_start,
                'velocidad_maquina': self.interior.velocidad_maquina,
                'cantidad_paginas': self.interior.cantidad_paginas,
                'trabajos_por_pliego': self.interior.producto_papel.trabajos_por_pliego,
                'pliegos_netos': self.interior.pliegos_netos,
                'cantidad_hojas': self.interior.producto_papel.cantidad_hojas,
                'cantidad_planchas': self.interior.cantidad_planchas + self.interior.plancha_adicional,
                'desperdicio': self.interior.producto_papel.desperdicio,
                'pliegos_demasia_fija': lineas_venta['demasia_fija'],
                'pliegos_demasia_variable': lineas_venta['demasia_variable'],
                'tiempo_arranque':  lineas_venta['tiempo_arranque'],
                'tiempo_impresion':  lineas_venta['tiempo_impresion'],
                'cantidad_tinta':  lineas_venta['cantidad_tinta'],
            }

        if hasattr(self.interior, 'doblado') != False and self.interior.doblado is not None:
            orden_trabajo_line['doblado'] = self.interior.doblado.id

        if hasattr(self.interior, 'encuadernado') != False and self.interior.encuadernado is not None:
            orden_trabajo_line['encuadernado'] = self.interior.encuadernado.id
            orden_trabajo_line['cantidad_broches'] = self.interior.cantidad_broches

        if hasattr(self.interior, 'laminado') != False and self.interior.laminado is not None:
            orden_trabajo_line['laminado'] = self.interior.laminado.id
            orden_trabajo_line['laminado_orientacion'] = self.interior.laminado_orientacion

        OrdenTrabajo.create([orden_trabajo_line])

    def crear_otra_cantidad_base(self, sale):
        # Si no existe otra cantidad con la cantidad de cantidad base, crearla
        pool = Pool()
        t = Transaction()
        if not sale.cantidad in [c.cantidad for c in sale.otra_cantidad]:
            cantidad_nueva = {'cantidad': sale.cantidad,
                                'utilidad': 30,
                                'sale_id': t.context['active_id']}
            OtraCantidad = pool.get('sale_printery_budget.otra_cantidad')
            OtraCantidad.create([cantidad_nueva])

    def borrar_productos_temporales(self, id_wizard_start='0'):
        pool = Pool()
        CalcularPapelProducto = pool.get('sale_printery_budget.calcular_papel.producto')
        productos_a_borrar = CalcularPapelProducto.search([('id_wizard', '=',
                                                        id_wizard_start)])
        CalcularPapelProducto.delete(productos_a_borrar)

    def creo_lineas_de_venta(self):

        # Sacar datos del producto.
        # Generar la linea de papel.
        # Borrar productos temporales.
        pool = Pool()
        t = Transaction()
        sale_line = {}
        Product = pool.get('product.product')
        SaleLine = pool.get('sale.line')
        CalcularPapelProducto = pool.get('sale_printery_budget.calcular_papel.producto')
        papel_producto_wizard = CalcularPapelProducto.search([('id', '=',
                                                        self.interior.producto_papel.id)])[0]
        papel = Product.search([('id', '=',
                                papel_producto_wizard.producto_id)])[0]
        res = {}

        # Creamos línea de papel (variable)
        sale_line = {
                'sale': t.context.get('active_id'),
                'sequence': 0,
                'type': 'line',
                'quantity': papel_producto_wizard.cantidad_hojas,
                'product': papel.id,
                'unit': papel.sale_uom,
                'unit_price': papel.list_price,
                'description': 'Papel, Desperdicio (%): ' + str(papel_producto_wizard.desperdicio),
                'fijo': False,
                'id_interior': self.interior.id_wizard_start,
                }
        SaleLine.create([sale_line])

        # Creamos línea de Planchas
        if self.interior.plancha_adicional is None:
            self.interior.plancha_adicional = 0
        planchas_totales = self.interior.cantidad_planchas + self.interior.plancha_adicional

        res['planchas_totales'] = planchas_totales
        description = u'Plancha'
        fijo = True
        self._save_sale_line(SaleLine, t, self.interior.maquina.plancha, planchas_totales, description, fijo)

        # Creamos línea de Pliegos Demasia Fija
        # Cantidad de Planchas * Cantidad de Pliegos en maquina.
        demasia_fija = self.interior.demasia_fija * planchas_totales
        res['demasia_fija'] = demasia_fija
        sale_line = {
                'sale': t.context.get('active_id'),
                'sequence': 0,
                'type': 'line',
                'quantity': demasia_fija,
                'product': papel.id,
                'unit': papel.sale_uom,
                'unit_price': papel.list_price,
                'description': 'Pliegos Demasia Fija',
                'fijo': True,
                'id_interior': self.interior.id_wizard_start,
                }
        SaleLine.create([sale_line])

        # Creamos línea de Pliegos Demasia Variable
        # (Demasia Variable * Cantidad de Pliegos en maquina). // 100
        demasia_variable = (self.interior.demasia_variable * self.interior.producto_papel.cantidad_de_pliegos) // 100
        res['demasia_variable'] = demasia_variable
        sale_line = {
                'sale': t.context.get('active_id'),
                'sequence': 0,
                'type': 'line',
                'quantity': demasia_variable,
                'product': papel.id,
                'unit': papel.sale_uom,
                'unit_price': papel.list_price,
                'description': 'Pliegos Demasia Variable',
                'fijo': False,
                'id_interior': self.interior.id_wizard_start,
                }
        SaleLine.create([sale_line])

        # Tiempo de impresión en maquina.
        # 1. Calcular cantidad de pasadas:
        # cantidad_pasadas = (colores_frente/colores_pasada) +
        # (colores_dorso/colores_pasada)
        # El sistema debe redondear al entero superior siempre.
        # Ej: cantidad_pasadas = (5/4) + (5/4) =  2+2 = 4
        # Los pliegos van a pasar 4 veces por la máquina.
        # => 1000 * 4 = 4000 pliegos
        # => tiempo_impresion = 4000 pliegos / velocidad_maquina

        cantidad_pasadas = ceil((Decimal(self.interior.colores_frente) / Decimal(self.interior.maquina.colores))) \
            + ceil((Decimal(self.interior.colores_dorso) / Decimal(self.interior.maquina.colores)))

        velocidad_maquina = getattr(self.interior.maquina, self.interior.velocidad_maquina)

        tiempo_impresion =  (Decimal(self.interior.producto_papel.cantidad_de_pliegos + demasia_variable + demasia_fija) * Decimal(cantidad_pasadas)) / Decimal(velocidad_maquina)

        res['tiempo_impresion'] = tiempo_impresion.quantize(Decimal('.01'))
        description = u'Tiempo de impresión máquina'
        fijo = False
        self._save_sale_line(SaleLine, t, self.interior.maquina, tiempo_impresion.quantize(Decimal('.01')), description, fijo)

        # Creamos línea de Tinta
        ## Formula:
        cantidad_tinta = Decimal(self.interior.producto_papel.ancho_pliego / 100) * Decimal(self.interior.producto_papel.alto_pliego / 100) * \
                        Decimal(self.interior.producto_papel.cantidad_de_pliegos + demasia_variable + demasia_fija) * Decimal(cantidad_pasadas) * \
                        Decimal(self.interior.tinta.rendimiento_tinta) / 1000 * Decimal(self.interior.tinta_superficie_cubierta / 100.0)

        ## ancho_pliego(metros) * alto_pliego(metros) -> area de pliego *
        ## cantidad_de_pliegos * rendimiento_tinta (gramos/m2) / 1000 *
        ## costo_kilo_tinta
        res['cantidad_tinta'] = cantidad_tinta.quantize(Decimal('.01'))

        description = u'Tinta'
        fijo = False
        self._save_sale_line(SaleLine, t, self.interior.tinta, cantidad_tinta.quantize(Decimal('.01')), description, fijo)

        # Tiempo de arranque máquina.
        # 1. Calcular cantidad de pasadas:
        # cantidad_pasadas = (colores_frente/colores_pasada) +
        # (colores_dorso/colores_pasada)
        # El sistema debe redondear al entero superior siempre.
        # Ej: cantidad_pasadas = (5/4) + (5/4) =  2+2 = 4
        # Los pliegos van a pasar 4 veces por la máquina.
        # => 1000 * 4 = 4000 pliegos
        # => tiempo_impresion = 4000 pliegos / velocidad_maquina
        # => tiempo_arranque en horas = cantidad_planchas * (cambio_de_plancha +
        # tiempo_preparacion) / 60
        tiempo_arranque = Decimal(planchas_totales) * Decimal((self.interior.maquina.cambio_de_plancha + self.interior.maquina.preparacion))
        tiempo_arranque = tiempo_arranque / Decimal(60)

        res['tiempo_arranque'] = tiempo_arranque.quantize(Decimal('.01'))
        description = u'Tiempo de arranque máquina'
        fijo = True
        self._save_sale_line(SaleLine, t, self.interior.maquina, tiempo_arranque.quantize(Decimal('.01')), description, fijo)

        # Doblado
        if self.interior.doblado:
            cantidad_doblado = self.interior.cantidad / self.interior.doblado.velocidad_maq
            description = u'Doblado'
            fijo = True
            self._save_sale_line(SaleLine, t, self.interior.doblado, cantidad_doblado.quantize(Decimal('.01')), description, fijo)

        # Encuadernacion
        # Broches: Cantidad de revistas x cantidad de broches por revista x valor del broche
        # Proceso: (cantidad de revistas/ velocidad de la maquina (revistas por hora)+ (paginas totales/ paginas por pliego)
        #           x tiempo arreglo (en hs) )* valor hora maquina
        # Ej.
        # Proceso:( 1000/1500+ (200/16) x 0,15 hs) x $300 el resultado de paginas totales/ paginas por pliego debe ser redondeado al entero mayor, por ej.
        # Si dá 2,5 el resultado debe ser 3 )
        if self.interior.categoria != 'folleto' and self.interior.encuadernado:
            broche = Product.search([('id', '=', self.interior.encuadernado.broche.id)])[0]
            cantidad_broches = self.interior.cantidad * self.interior.cantidad_broches

            description = u'Encuadernado (broches)'
            fijo = False
            self._save_sale_line(SaleLine, t, broche, cantidad_broches, description, fijo)

            cantidad_proceso = Decimal(self.interior.cantidad) / Decimal(self.interior.encuadernado.velocidad_maq) + Decimal(ceil(self.interior.cantidad_paginas / self.interior.producto_papel.pliegos_por_hoja)) \
                      * Decimal(self.interior.encuadernado.tiempo_arreglo)

            description = u'Encuadernado (proceso)'
            fijo = False
            self._save_sale_line(SaleLine, t, self.interior.encuadernado, cantidad_proceso.quantize(Decimal('.01')), description, fijo)

        if self.interior.laminado:
            # Material: área del pliego en metros cuadrados x cantidad de pliegos x costo por metro cuadrado
            # Material: (43,5 cm/100) x (60,4 cm/100) x 250 pliegos x 1 dólar
            material_laminado = Product.search([('id', '=', self.interior.laminado.material_laminado.id)])[0]
            cantidad_material_laminado = ceil((self.interior.producto_papel.ancho_pliego / 100) * (self.interior.producto_papel.alto_pliego / 100) * self.interior.producto_papel.cantidad_de_pliegos)

            description = u'Laminado (material)'
            fijo = False
            self._save_sale_line(SaleLine, t, material_laminado, cantidad_material_laminado, description, fijo)

            # Proceso:(Largo del pliego (en metros) x cantidad de pliegos / velocidad de maquina + tiempo de arreglo (en horas))*valor de la hora
            # Proceso: (0,604 mts x 250 / 300 mts x hs + 0,5 hs) x 250$
            cantidad_proceso = Decimal(self.interior.producto_papel.alto_pliego / 100) * Decimal(self.interior.producto_papel.cantidad_de_pliegos) / Decimal(self.interior.laminado.velocidad_maq) \
                      + Decimal(self.interior.laminado.tiempo_arreglo)

            description = u'Laminado (proceso)'
            fijo = False
            self._save_sale_line(SaleLine, t, self.interior.laminado, cantidad_proceso.quantize(Decimal('.01')), description, fijo)

        return res

    def _save_sale_line(self, SaleLine, t, producto, quantity, description, fijo):

            sale_line = {
                    'sale': t.context.get('active_id'),
                    'sequence': 0,
                    'type': 'line',
                    'quantity': quantity,
                    'product': producto,
                    'unit': producto.sale_uom,
                    'unit_price': producto.list_price,
                    'description': description,
                    'fijo': fijo,
                    'id_interior': self.interior.id_wizard_start,
                    }
            SaleLine.create([sale_line])
