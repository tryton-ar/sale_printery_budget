#This file is part sale_printery_budget module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .product import *
from .sale import *
from .trabajo import *

def register():
    Pool.register(
        Template,
        OtraCantidad,
        Sale,
        SaleLine,
        OrdenTrabajo,
        CalcularPapelWizard,
        CalcularPapelProducto,
        CalcularPapelElegirInterior,
        module='sale_printery_budget', type_='model')
    Pool.register(
        OrdenTrabajoReport,
        PresupuestoClienteReport,
        module='sale_printery_budget', type_='report')
    Pool.register(
        CalcularPapel,
        RetomarCalcularPapel,
        module='sale_printery_budget', type_='wizard')
