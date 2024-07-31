# This file is part sale_printery_budget module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import (
    product, sale, trabajo)


def register():
    Pool.register(
        product.Template,
        sale.OtraCantidad,
        sale.Sale,
        sale.SaleLine,
        sale.CalcularPapelWizard,
        sale.CalcularPapelProducto,
        sale.CalcularPapelElegirInterior,
        trabajo.OrdenTrabajo,
        module='sale_printery_budget', type_='model')
    Pool.register(
        trabajo.OrdenTrabajoReport,
        sale.PresupuestoClienteReport,
        module='sale_printery_budget', type_='report')
    Pool.register(
        sale.CalcularPapel,
        sale.RetomarCalcularPapel,
        module='sale_printery_budget', type_='wizard')
