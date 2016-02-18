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

class utils():

    interior = {}

    def test(self):
        print "testeando" + str(self.interior.calle_horizontal)

    def creo_orden_trabajo(cls, sale, lineas_venta):
        "Crear orden de trabajo basado en el papel elegido"
        print "Creo orden trabajo"
        pool = Pool()
        t = Transaction()
        orden_trabajo_line = {}
        orden_trabajo_obj = pool.get('sale_printery_budget.orden_trabajo')
        orden_trabajo_line = {
                'sale':  t.context.get('active_id'),
                'state': 'draft',
                'calle_horizontal': cls.interior.calle_horizontal,
                'calle_vertical': cls.interior.calle_vertical,
                'cantidad': cls.interior.cantidad,
                'colores_frente': cls.interior.colores_frente,
                'colores_dorso': cls.interior.colores_dorso,
                'es_tapa': cls.interior.es_tapa,
                'tipo_papel': cls.interior.tipo_papel.id,
                'producto_papel': cls.interior.producto_papel.producto_id,
                'sin_pinza': cls.interior.sin_pinza,
                'formato_pliego': cls.interior.formato_pliego,
                'categoria': cls.interior.categoria,
                'ancho': cls.interior.ancho,
                'altura': cls.interior.altura,
                'postura_papel': cls.interior.postura_papel,
                'postura_trabajo': cls.interior.postura_trabajo,
                'maquina': cls.interior.maquina.id,
                'tinta_superficie_cubierta': cls.interior.tinta_superficie_cubierta,
                'tinta': cls.interior.tinta.id,
                'solapa': cls.interior.solapa,
                'lomo': cls.interior.lomo,
                'gramaje': cls.interior.gramaje,
                'id_interior': cls.interior.id_wizard_start,
                'velocidad_maquina': cls.interior.velocidad_maquina,
                'cantidad_paginas': cls.interior.cantidad_paginas,
                'trabajos_por_pliego': cls.interior.producto_papel.trabajos_por_pliego,
                'pliegos_netos': cls.interior.pliegos_netos,
                'cantidad_hojas': cls.interior.producto_papel.cantidad_hojas,
                'cantidad_planchas': cls.interior.cantidad_planchas + cls.interior.plancha_adicional,
                'desperdicio': cls.interior.producto_papel.desperdicio,
                'pliegos_demasia_fija': lineas_venta['demasia_fija'],
                'pliegos_demasia_variable': lineas_venta['demasia_variable'],
                'tiempo_arranque':  lineas_venta['tiempo_arranque'],
                'tiempo_impresion':  lineas_venta['tiempo_impresion'],
                'cantidad_tinta':  lineas_venta['cantidad_tinta'],
            }

        if hasattr(cls.interior, 'doblado') != False and cls.interior.doblado is not None:
            orden_trabajo_line['doblado'] = cls.interior.doblado.id

        if hasattr(cls.interior, 'encuadernado') != False and cls.interior.encuadernado is not None:
            orden_trabajo_line['encuadernado'] = cls.interior.encuadernado.id
            orden_trabajo_line['cantidad_broches'] = cls.interior.cantidad_broches

        if hasattr(cls.interior, 'laminado') != False and cls.interior.laminado is not None:
            orden_trabajo_line['laminado'] = cls.interior.laminado.id
            orden_trabajo_line['laminado_orientacion'] = cls.interior.laminado_orientacion

        orden_trabajo_obj.create([orden_trabajo_line])

    def crear_otra_cantidad_base(cls, sale):
        # Si no existe otra cantidad con la cantidad de cantidad base, crearla
        pool = Pool()
        t = Transaction()
        if not sale.cantidad in [c['cantidad'] for c in sale.otra_cantidad]:
            cantidad_nueva = {'cantidad': sale.cantidad,
                                'utilidad': 30,
                                'sale_id': t.context['active_id']}
            cantidades_obj = pool.get('sale_printery_budget.otra_cantidad')
            cantidades_obj.create([cantidad_nueva])

    def borrar_productos_temporales(self, id_wizard_start='0'):
        pool = Pool()
        producto_wiz_obj = pool.get('sale_printery_budget.calcular_papel.producto')
        productos_a_borrar = producto_wiz_obj.search([('id_wizard', '=',
                                                        id_wizard_start)])
        producto_wiz_obj.delete(productos_a_borrar)

    def creo_lineas_de_venta(cls):

        # Sacar datos del producto.
        # Generar la linea de papel.
        # Borrar productos temporales.
        pool = Pool()
        t = Transaction()
        sale_line = {}
        producto_obj = pool.get('product.product')
        sale_line_obj = pool.get('sale.line')
        producto_wiz_obj = pool.get('sale_printery_budget.calcular_papel.producto')
        papel_producto_wizard = producto_wiz_obj.search([('id', '=',
                                                        cls.interior.producto_papel.id)])[0]
        papel = producto_obj.search([('id', '=',
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
                'id_interior': cls.interior.id_wizard_start,
                }
        sale_line_obj.create([sale_line])

        # Creamos línea de Planchas
        if cls.interior.plancha_adicional is not 0 or cls.interior.plancha_adicional is not None:
            planchas_totales = cls.interior.cantidad_planchas + cls.interior.plancha_adicional
        else:
            planchas_totales = cls.interior.cantidad_planchas

        res['planchas_totales'] = planchas_totales
        description = u'Plancha'
        fijo = True
        cls._save_sale_line(sale_line_obj, t, cls.interior.maquina.plancha, planchas_totales, description, fijo)

        # Creamos línea de Pliegos Demasia Fija
        # Cantidad de Planchas * Cantidad de Pliegos en maquina.
        demasia_fija = cls.interior.demasia_fija * planchas_totales
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
                'id_interior': cls.interior.id_wizard_start,
                }
        sale_line_obj.create([sale_line])

        # Creamos línea de Pliegos Demasia Variable
        # (Demasia Variable * Cantidad de Pliegos en maquina). // 100
        demasia_variable = (cls.interior.demasia_variable * cls.interior.producto_papel.cantidad_de_pliegos) // 100
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
                'id_interior': cls.interior.id_wizard_start,
                }
        sale_line_obj.create([sale_line])

        # Tiempo de impresión en maquina.
        # 1. Calcular cantidad de pasadas:
        # cantidad_pasadas = (colores_frente/colores_pasada) +
        # (colores_dorso/colores_pasada)
        # El sistema debe redondear al entero superior siempre.
        # Ej: cantidad_pasadas = (5/4) + (5/4) =  2+2 = 4
        # Los pliegos van a pasar 4 veces por la máquina.
        # => 1000 * 4 = 4000 pliegos
        # => tiempo_impresion = 4000 pliegos / velocidad_maquina

        cantidad_pasadas = ceil((Decimal(cls.interior.colores_frente) / Decimal(cls.interior.maquina.colores))) \
            + ceil((Decimal(cls.interior.colores_dorso) / Decimal(cls.interior.maquina.colores)))

        velocidad_maquina = getattr(cls.interior.maquina, cls.interior.velocidad_maquina)

        tiempo_impresion =  (Decimal(cls.interior.producto_papel.cantidad_de_pliegos + demasia_variable + demasia_fija) * Decimal(cantidad_pasadas)) / Decimal(velocidad_maquina)

        res['tiempo_impresion'] = tiempo_impresion.quantize(Decimal('.01'))
        description = u'Tiempo de impresión máquina'
        fijo = False
        cls._save_sale_line(sale_line_obj, t, cls.interior.maquina, tiempo_impresion.quantize(Decimal('.01')), description, fijo)

        # Creamos línea de Tinta
        ## Formula:
        cantidad_tinta = Decimal(cls.interior.producto_papel.ancho_pliego / 100) * Decimal(cls.interior.producto_papel.alto_pliego / 100) * \
                        Decimal(cls.interior.producto_papel.cantidad_de_pliegos + demasia_variable + demasia_fija) * Decimal(cantidad_pasadas) * \
                        Decimal(cls.interior.tinta.rendimiento_tinta) / 1000 * Decimal(cls.interior.tinta_superficie_cubierta / 100.0)

        ## ancho_pliego(metros) * alto_pliego(metros) -> area de pliego *
        ## cantidad_de_pliegos * rendimiento_tinta (gramos/m2) / 1000 *
        ## costo_kilo_tinta
        res['cantidad_tinta'] = cantidad_tinta.quantize(Decimal('.01'))

        description = u'Tinta'
        fijo = False
        cls._save_sale_line(sale_line_obj, t, cls.interior.tinta, cantidad_tinta.quantize(Decimal('.01')), description, fijo)

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
        tiempo_arranque = Decimal(planchas_totales) * Decimal((cls.interior.maquina.cambio_de_plancha + cls.interior.maquina.preparacion))
        tiempo_arranque = tiempo_arranque / Decimal(60)

        res['tiempo_arranque'] = tiempo_arranque.quantize(Decimal('.01'))
        description = u'Tiempo de arranque máquina'
        fijo = True
        cls._save_sale_line(sale_line_obj, t, cls.interior.maquina, tiempo_arranque.quantize(Decimal('.01')), description, fijo)

        # Doblado
        if cls.interior.doblado:
            cantidad_doblado = cls.interior.cantidad / cls.interior.doblado.velocidad_maq
            description = u'Doblado'
            fijo = True
            cls._save_sale_line(sale_line_obj, t, cls.interior.doblado, cantidad_doblado.quantize(Decimal('.01')), description, fijo)

        # Encuadernacion
        # Broches: Cantidad de revistas x cantidad de broches por revista x valor del broche
        # Proceso: (cantidad de revistas/ velocidad de la maquina (revistas por hora)+ (paginas totales/ paginas por pliego)
        #           x tiempo arreglo (en hs) )* valor hora maquina
        # Ej.
        # Proceso:( 1000/1500+ (200/16) x 0,15 hs) x $300 el resultado de paginas totales/ paginas por pliego debe ser redondeado al entero mayor, por ej.
        # Si dá 2,5 el resultado debe ser 3 )
        if cls.interior.categoria != 'folleto' and cls.interior.encuadernado:
            broche = producto_obj.search([('id', '=', cls.interior.encuadernado.broche.id)])[0]
            cantidad_broches = cls.interior.cantidad * cls.interior.cantidad_broches

            description = u'Encuadernado (broches)'
            fijo = False
            cls._save_sale_line(sale_line_obj, t, broche, cantidad_broches, description, fijo)

            cantidad_proceso = Decimal(cls.interior.cantidad) / Decimal(cls.interior.encuadernado.velocidad_maq) + Decimal(ceil(cls.interior.cantidad_paginas / cls.interior.producto_papel.pliegos_por_hoja)) \
                      * Decimal(cls.interior.encuadernado.tiempo_arreglo)

            description = u'Encuadernado (proceso)'
            fijo = False
            cls._save_sale_line(sale_line_obj, t, cls.interior.encuadernado, cantidad_proceso.quantize(Decimal('.01')), description, fijo)

        if cls.interior.laminado:
            # Material: área del pliego en metros cuadrados x cantidad de pliegos x costo por metro cuadrado
            # Material: (43,5 cm/100) x (60,4 cm/100) x 250 pliegos x 1 dólar
            material_laminado = producto_obj.search([('id', '=', cls.interior.laminado.material_laminado.id)])[0]
            cantidad_material_laminado = ceil((cls.interior.producto_papel.ancho_pliego / 100) * (cls.interior.producto_papel.alto_pliego / 100) * cls.interior.producto_papel.cantidad_de_pliegos)

            description = u'Laminado (material)'
            fijo = False
            cls._save_sale_line(sale_line_obj, t, material_laminado, cantidad_material_laminado, description, fijo)

            # Proceso:(Largo del pliego (en metros) x cantidad de pliegos / velocidad de maquina + tiempo de arreglo (en horas))*valor de la hora
            # Proceso: (0,604 mts x 250 / 300 mts x hs + 0,5 hs) x 250$
            cantidad_proceso = Decimal(cls.interior.producto_papel.alto_pliego / 100) * Decimal(cls.interior.producto_papel.cantidad_de_pliegos) / Decimal(cls.interior.laminado.velocidad_maq) \
                      + Decimal(cls.interior.laminado.tiempo_arreglo)

            description = u'Laminado (proceso)'
            fijo = False
            cls._save_sale_line(sale_line_obj, t, cls.interior.laminado, cantidad_proceso.quantize(Decimal('.01')), description, fijo)

        return res

    def _save_sale_line(cls, sale_line_obj, t, producto, quantity, description, fijo):

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
                    'id_interior': cls.interior.id_wizard_start,
                    }
            sale_line_obj.create([sale_line])
