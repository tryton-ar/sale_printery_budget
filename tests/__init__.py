# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.sale_printery_budget.tests.test_sale_printery_budget import suite
except ImportError:
    from .test_sale_printery_budget import suite

__all__ = ['suite']
