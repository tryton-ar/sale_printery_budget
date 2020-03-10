=============
Sale Scenario
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard, Report
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install sale::

    >>> config = activate_modules('sale_printery_budget')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.save()
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Cash'
    >>> payment_method.journal = cash_journal
    >>> payment_method.credit_account = cash
    >>> payment_method.debit_account = cash
    >>> payment_method.save()

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create account categories::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category OBRA")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

    >>> account_category_tax, = account_category.duplicate()
    >>> account_category_tax.customer_taxes.append(tax)
    >>> account_category_tax.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> unit_hour, = ProductUom.find([('symbol', '=', 'h')])
    >>> unit_minute, = ProductUom.find([('symbol', '=', 'min')])
    >>> unit_centimetro, = ProductUom.find([('symbol', '=', 'cm')])
    >>> unit_gramo, = ProductUom.find([('symbol', '=', 'g')])
    >>> unit_kilogramo, = ProductUom.find([('symbol', '=', 'kg')])
    >>> ProductTemplate = Model.get('product.template')

Create product utilidad::

    >>> template = ProductTemplate()
    >>> template.name = 'Utilidad'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.product_type_printery = 'utilidad'
    >>> template.salable = True
    >>> template.list_price = Decimal('1')
    >>> template.genera_contribucion_marginal = True
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product_utilidad, = template.products

Create product tinta::

    >>> template = ProductTemplate()
    >>> template.name = 'Tinta Proceso'
    >>> template.default_uom = unit_kilogramo
    >>> template.type = 'goods'
    >>> template.product_type_printery = 'tinta'
    >>> template.salable = True
    >>> template.list_price = Decimal('60')
    >>> template.rendimiento_tinta = 2
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product_tinta, = template.products

Create product plancha::

    >>> template = ProductTemplate()
    >>> template.name = 'Plancha Base'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.product_type_printery = 'plancha'
    >>> template.salable = True
    >>> template.list_price = Decimal('200')
    >>> template.pliegos_por_plancha = 50000
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product_plancha, = template.products

Create product MAQUINA SAKURAI::

    >>> template = ProductTemplate()
    >>> template.name = 'SAKURAI'
    >>> template.default_uom = unit_hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.consumable = True
    >>> template.list_price = Decimal('400')
    >>> template.account_category = account_category_tax
    >>> template.genera_contribucion_marginal = True
    >>> template.product_type_printery = 'maquina'
    >>> template.cambio_de_plancha = 20
    >>> template.cambio_de_plancha_uom = unit_minute
    >>> template.preparacion = 20
    >>> template.preparacion_uom = unit_minute
    >>> template.tiempo_rapido = 8000
    >>> template.tiempo_medio = 5000
    >>> template.tiempo_lento = 2000
    >>> template.width_max = float('102')
    >>> template.width_min = float('55')
    >>> template.height_max = float('72')
    >>> template.height_min = float('35')
    >>> template.maquina_uom = unit_centimetro
    >>> template.colores = 4
    >>> template.pinza = float('1')
    >>> template.cola = float('5')
    >>> template.laterales = float('1')
    >>> template.demasia_fija = 50
    >>> template.demasia_variable = 3
    >>> template.save()
    >>> template.plancha = product_plancha
    >>> template.save()
    >>> product_maquina, = template.products

Create product Papel 65x95 100gr::

    >>> template = ProductTemplate()
    >>> template.name = 'PAPEL 65x95cm 100gr'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.consumable = True
    >>> template.product_type_printery = 'papel'
    >>> template.list_price = Decimal('1200')
    >>> template.account_category = account_category_tax
    >>> template.genera_contribucion_marginal = False
    >>> template.width = float('65')
    >>> template.width_uom = unit_centimetro
    >>> template.height = float('95')
    >>> template.height_uom = unit_centimetro
    >>> template.weight = float('100')
    >>> template.weight_uom = unit_gramo
    >>> # template.info_ratio = round(float(float('0.65') * float('0.95') * float('100') / 1000), 4)
    >>> # template.info_list_price = Decimal('11')
    >>> template.save()
    >>> product_papel, = template.products

Create product Broche::

    >>> template = ProductTemplate()
    >>> template.name = 'Broche Base'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.consumable = True
    >>> template.product_type_printery = 'broche'
    >>> template.list_price = Decimal('30')
    >>> template.genera_contribucion_marginal = False
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product_broche, = template.products

Create product encuadernado::

    >>> template = ProductTemplate()
    >>> template.name = 'Encuadernado'
    >>> template.default_uom = unit_hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.product_type_printery = 'maquina_encuadernacion'
    >>> template.list_price = Decimal('400')
    >>> template.account_category = account_category_tax
    >>> template.genera_contribucion_marginal = True
    >>> template.velocidad_maq = Decimal('2000')
    >>> template.tiempo_arreglo = Decimal('0.5')
    >>> template.broche = product_broche
    >>> template.save()
    >>> product_encuadernado, = template.products

Create product doblado diptico::

    >>> template = ProductTemplate()
    >>> template.name = 'Doblado Diptico'
    >>> template.default_uom = unit_hour
    >>> template.type = 'service'
    >>> template.salable = True
    >>> template.product_type_printery = 'maquina_doblado'
    >>> template.list_price = Decimal('120')
    >>> template.account_category = account_category_tax
    >>> template.genera_contribucion_marginal = True
    >>> template.velocidad_maq = Decimal('6000')
    >>> template.tiempo_arreglo = Decimal('0.5')
    >>> template.save()
    >>> product_doblado, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create an Inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> Location = Model.get('stock.location')
    >>> storage, = Location.find([
    ...         ('code', '=', 'STO'),
    ...         ])
    >>> inventory = Inventory()
    >>> inventory.location = storage
    >>> inventory_line = inventory.lines.new(product=product_tinta)
    >>> inventory_line.quantity = 100.0
    >>> inventory_line.expected_quantity = 0.0
    >>> inventory_line = inventory.lines.new(product=product_plancha)
    >>> inventory_line.quantity = 1000.0
    >>> inventory_line.expected_quantity = 0.0
    >>> inventory.click('confirm')
    >>> inventory.state
    'done'

Create a sale::

    >>> Sale = Model.get('sale.sale')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale.cantidad = 1000
    >>> sale.save()

Wizard printery budget::

    >>> Papel = Model.get('sale_printery_budget.calcular_papel.producto')
    >>> calcular_papel = Wizard('sale_printery_budget.calcular_papel', [sale])
    >>> calcular_papel.form.categoria = 'folleto'
    >>> calcular_papel.form.altura = Decimal(15)
    >>> calcular_papel.form.ancho = Decimal(10)
    >>> calcular_papel.form.sin_pinza = False
    >>> calcular_papel.form.cantidad = 1000
    >>> calcular_papel.form.tipo_papel = account_category_tax
    >>> calcular_papel.form.gramaje = Decimal('100')
    >>> calcular_papel.form.colores_frente = 4
    >>> calcular_papel.form.colores_dorso = 2
    >>> calcular_papel.form.demasia_variable = 200
    >>> calcular_papel.form.demasia_fija = 10
    >>> calcular_papel.form.tinta = product_tinta
    >>> calcular_papel.form.tinta_superficie_cubierta = 20
    >>> calcular_papel.form.velocidad_maquina = 'tiempo_medio'
    >>> calcular_papel.form.maquina = product_maquina
    >>> calcular_papel.form.plancha_adicional = 2
    >>> calcular_papel.form.postura_trabajo = 'H'
    >>> calcular_papel.form.postura_papel = 'H'
    >>> producto_papel_wiz = Papel.find([])[0]
    >>> calcular_papel.form.producto_papel = producto_papel_wiz
    >>> calcular_papel.execute('terminar')
    >>> sale.reload()
    >>> sale.click('quote')

Confirm cantidad and process sale::

    >>> OtraCantidad = Model.get('sale_printery_budget.otra_cantidad')
    >>> cantidad_confirmada = OtraCantidad.find([])[0]
    >>> sale.cantidad_confirmada = cantidad_confirmada
    >>> sale.click('confirm')
    >>> sale.state
    'processing'

Testing the report::

    >>> sale_report = Report('sale_printery_budget.presupuesto_cliente')
    >>> ext, _, _, name = sale_report.execute([sale], {})
    >>> ext
    'odt'
    >>> name
    'Presupuesto al Cliente'

Process orden de trabajo::

    >>> OrdenTrabajo = Model.get('sale_printery_budget.orden_trabajo')
    >>> orden_trabajo = OrdenTrabajo.find([])
    >>> orden_trabajo, = OrdenTrabajo.find([
    ...         ('sale', '=', sale),
    ...         ])
    >>> orden_trabajo.click('confirmed')
    >>> orden_trabajo.click('process')
    >>> orden_trabajo.click('done')
    >>> orden_trabajo.state
    'done'

Testing Orden Trabajo report::

    >>> trabajo_report = Report('sale_printery_budget.orden_trabajo')
    >>> ext, _, _, name = trabajo_report.execute([orden_trabajo], {})
    >>> ext
    'odt'
    >>> name
    'Orden de trabajo'
