# coding=utf-8
# Scenario sale_printery_budget

# Imports
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
#from operator import attrgetter
from proteus import config, Model, Wizard
today = datetime.date.today()

# Database
config = config.set_trytond('tryton32_imprentas', database_type='postgresql', config_file='/etc/trytond-3.2.conf', language='es_AR')

Lang = Model.get('ir.lang')
(es_AR,) = Lang.find([('code', '=', 'es_AR')])
es_AR.translatable = True
es_AR.save()

# Install Module `sale_printery_budget`
Module = Model.get('ir.module.module')
module, = Module.find([('name', '=', 'sale')])
module.click('install')
module, = Module.find([('name', '=', 'sale_printery_budget')])
module.click('install')
module, = Module.find([('name', '=', 'account_coop_ar')])
module.click('install')
module, = Module.find([('name', '=', 'purchase')])
module.click('install')
module, = Module.find([('name', '=', 'account_invoice_ar')])
module.click('install')
module, = Module.find([('name', '=', 'account_check_ar')])
module.click('install')
module, = Module.find([('name', '=', 'account_voucher_ar')])
module.click('install')
module, = Module.find([('name', '=', 'account_retencion_ar')])
module.click('install')
module, = Module.find([('name', '=', 'account_bank_ar')])
module.click('install')
module, = Module.find([('name', '=', 'country_ar')])
module.click('install')
module, = Module.find([('name', '=', 'account_invoice_information_uom')])
module.click('install')
module, = Module.find([('name', '=', 'purchase_information_uom')])
module.click('install')
Wizard('ir.module.module.install_upgrade').execute('upgrade')

print u'\n>>> wizards de configuracion se marcan como done...'
ConfigWizardItem = Model.get('ir.module.module.config_wizard.item')
for item in ConfigWizardItem.find([('state', '!=', 'done')]):
    item.state = 'done'
    item.save()

# Create Company
# Obtener nombre de la compania de un archivo.

Currency = Model.get('currency.currency')
CurrencyRate = Model.get('currency.currency.rate')
currencies = Currency.find([('code', '=', 'ARS')])
currency, = currencies
Company = Model.get('company.company')
Party = Model.get('party.party')
company_config = Wizard('company.company.config')
company_config.execute('company')
company = company_config.form
party = Party(name=u'Red Gráfica Cooperativa Limitada')
party.lang = es_AR

print u'Configuramos company account_invoice_ar'
party.company_name = party.name
party.vat_country = 'AR'
party.vat_number = '30710659644'
party.iva_condition = 'responsable_inscripto'
party.company_type = 'cooperativa'
#party.primary_activity_code = '181109' #  IMPRESIÓN N.C.P., EXCEPTO DE DIARIOS Y REVISTAS
#party.start_activity_date
#party.controlling_entity
#party.controlling_entity_number
#party.iibb_type
#party.iibb_number

print u'Configuramos company address account_invoice_ar'

party.addresses.street = "Paseo colón 731 - piso 4°"
party.addresses.zip = 'C1063ACH'
party.addresses.country = '191'
party.addresses.city = 'CABA'
party.save()

company.party = party
company.currency = currency
company_config.execute('add')

print "Instalo modulo cooperative_ar"
module, = Module.find([('name', '=', 'cooperative_ar')])
module.click('install')
Wizard('ir.module.module.install_upgrade').execute('upgrade')

company, = Company.find([])

# Reload the context

User = Model.get('res.user')
Group = Model.get('res.group')
config._context = User.get_preferences(True, config.context)

admin_user = User.find()[0]
admin_user.language = es_AR
admin_user.password = 'admin'
admin_user.save()

# Crear Usuario vendedor:

#sale_user = User()
#sale_user.name = 'Sale'
#sale_user.login = 'sale'
#sale_user.main_company = company
#sale_group, = Group.find([('name', '=', 'Sales')])
#sale_user.groups.append(sale_group)
#sale_user.save()
#
## Create stock user::
#
#stock_user = User()
#stock_user.name = 'Stock'
#stock_user.login = 'stock'
#stock_user.main_company = company
#stock_group, = Group.find([('name', '=', 'Stock')])
#stock_user.groups.append(stock_group)
#stock_user.save()
#
## Create account user::
#
#account_user = User()
#account_user.name = 'Account'
#account_user.login = 'account'
#account_user.main_company = company
#account_group, = Group.find([('name', '=', 'Account')])
#account_user.groups.append(account_group)
#account_user.save()

# Create fiscal year:

FiscalYear = Model.get('account.fiscalyear')
Sequence = Model.get('ir.sequence')
SequenceStrict = Model.get('ir.sequence.strict')
fiscalyear = FiscalYear(name=str(today.year))
fiscalyear.start_date = today + relativedelta(month=1, day=1)
fiscalyear.end_date = today + relativedelta(month=12, day=31)
fiscalyear.company = company
post_move_seq = Sequence(name=str(today.year), code='account.move',
    company=company)
post_move_seq.save()
receipt_seq = Sequence(name='Recibo Cooperativa', code='account.invoice',
    company=company)
receipt_seq.save()
fiscalyear.receipt_sequence = receipt_seq
fiscalyear.post_move_sequence = post_move_seq
invoice_seq = SequenceStrict(name=str(today.year),
    code='account.invoice', company=company)
invoice_seq.save()
fiscalyear.out_invoice_sequence = invoice_seq
fiscalyear.in_invoice_sequence = invoice_seq
fiscalyear.out_credit_note_sequence = invoice_seq
fiscalyear.in_credit_note_sequence = invoice_seq
fiscalyear.save()
FiscalYear.create_period([fiscalyear.id], config.context)

# Create chart of accounts::

AccountTemplate = Model.get('account.account.template')
Account = Model.get('account.account')
Journal = Model.get('account.journal')
account_template, = AccountTemplate.find([('parent', '=', None), ('name', '=', 'Plan Contable Argentino para Cooperativas')])
#account_template, = AccountTemplate.find([('parent', '=', None)])
create_chart = Wizard('account.create_chart')
create_chart.execute('account')
create_chart.form.account_template = account_template
create_chart.form.company = company
create_chart.execute('create_account')
receivable, = Account.find([
        ('kind', '=', 'receivable'),
        ('code', '=', '1131'), # Deudores por servicios
        ('company', '=', company.id),
        ])
payable, = Account.find([
        ('kind', '=', 'payable'),
        ('code', '=', '2111'), # Proveedores
        ('company', '=', company.id),
        ])
revenue, = Account.find([
        ('kind', '=', 'revenue'),
        ('code', '=', '511'), # Ingresos por servicios realizados
        ('company', '=', company.id),
        ])
expense, = Account.find([
        ('kind', '=', 'expense'),
        ('code', '=', '5249'), # Gastos Varios
        ('company', '=', company.id),
        ])
create_chart.form.account_receivable = receivable
create_chart.form.account_payable = payable
create_chart.execute('create_properties')
cash, = Account.find([
        ('kind', '=', 'stock'),
        ('name', '=', 'Caja'),
        ('code', '=', '1111'),
        ('company', '=', company.id),
        ])
cash_journal, = Journal.find([('type', '=', 'cash')])
cash_journal.credit_account = cash
cash_journal.debit_account = cash
cash_journal.save()

#Create parties::

#Party = Model.get('party.party')
#supplier = Party(name='Supplier')
#supplier.save()
#customer = Party(name='Customer')
#customer.save()

parent = 'PAPEL'

ProductCategory = Model.get('product.category')
category, = ProductCategory.find([('name', '=', parent)])
category.account_revenue = revenue
category.account_expense = expense
category.save()

category_parent, = ProductCategory.find([('name', '=', parent)])
category_child = ProductCategory(name='OBRA')
category_child.parent = category_parent
category_child.account_parent = True
category_child.save()

ProductUom = Model.get('product.uom')
unit, = ProductUom.find([('symbol', '=', 'u')])
unit_hour, = ProductUom.find([('symbol', '=', 'h')])
unit_minute, = ProductUom.find([('symbol', '=', 'min')])
unit_centimetro, = ProductUom.find([('symbol', '=', 'cm')])
unit_gramo, = ProductUom.find([('symbol', '=', 'g')])
unit_kilogramo, = ProductUom.find([('symbol', '=', 'kg')])

ProductTemplate = Model.get('product.template')
Product = Model.get('product.product')

# Crear producto Utilidad
#product = Product()
template = ProductTemplate()
template.name = 'Utilidad'
template.default_uom = unit
template.type = 'service'
template.product_type_printery = 'utilidad'
template.salable = True
template.list_price = Decimal('1')
template.cost_price = Decimal('1')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
template.genera_contribucion_marginal = True
template.save()
#product.template = template
#product.save()

# Crear producto Tinta Proceso
#product = Product()
template = ProductTemplate()
template.name = 'Tinta Proceso'
template.default_uom = unit_kilogramo
template.type = 'goods'
template.product_type_printery = 'tinta'
template.salable = True
template.purchasable = True
template.consumable = True
template.list_price = Decimal('60')
template.cost_price = Decimal('60')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
template.rendimiento_tinta = 2
template.save()
#product.template = template
#product.save()

# Crear producto Plancha Base
#product_plancha = Product()
template_plancha = ProductTemplate()
template_plancha.name = 'Plancha Base'
template_plancha.default_uom = unit
template_plancha.type = 'goods'
template_plancha.product_type_printery = 'plancha'
template_plancha.salable = True
template_plancha.purchasable = True
template_plancha.consumable = True
template_plancha.list_price = Decimal('200')
template_plancha.cost_price = Decimal('200')
template_plancha.cost_price_method = 'fixed'
template_plancha.account_expense = expense
template_plancha.account_revenue = revenue
template_plancha.pliegos_por_plancha = 50000
template_plancha.save()
#product_plancha.template = template
#product_plancha.save()

# Crear producto MAQUINA SAKURAI
#product = Product()
template = ProductTemplate()
template.name = 'SAKURAI'
template.default_uom = unit_hour
template.type = 'service'
template.product_type_printery = 'maquina'
template.salable = True
template.list_price = Decimal('400')
template.cost_price = Decimal('400')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
# Rellenar campos especificos de maquina
template.genera_contribucion_marginal = True
template.cambio_de_plancha = 20
template.cambio_de_plancha_uom = unit_minute
template.preparacion = 20
template.preparacion_uom = unit_minute
template.tiempo_rapido = 8000
template.tiempo_medio = 5000
template.tiempo_lento = 2000
template.width_max = float('102')
template.width_min = float('55')
template.height_max = float('72')
template.height_min = float('35')
template.maquina_uom = unit_centimetro
template.colores = 4
template.pinza = float('1')
template.cola = float('5')
template.laterales = float('1')
template.demasia_fija = 50
template.demasia_variable = 3
template.plancha = template_plancha.products[0]
template.save()

# Crear producto PAPEL
template = ProductTemplate()
template.name = 'PAPEL 65x95cm 100gram'
template.default_uom = unit
template.type = 'goods'
template.category = category_child
template.purchasable = True
template.salable = True
template.consumable = True
template.product_type_printery = 'papel'
#template.list_price = Decimal('0.05')
#template.cost_price = Decimal('0.08')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
# Rellenar campos especificos de PAPEL
template.genera_contribucion_marginal = False
template.width = float('65')
template.width_uom = unit_centimetro
template.height = float('95')
template.height_uom = unit_centimetro
template.weight = float('100')
template.weight_uom = unit_gramo
# uom information
# (ancho x alto x gramo) / 1000 = ratio
template.use_info_unit = True
template.info_unit = unit_kilogramo
#template.info_ratio = round(float(float('0.65') * float('0.95') * float('100') / 1000), 4)
template.info_list_price = Decimal('11')
template.cost_price = template.list_price
template.save()

# Crear producto PAPEL
template = ProductTemplate()
template.name = 'PAPEL 72x102cm 100 gr'
template.default_uom = unit
template.type = 'goods'
template.category = category_child
template.purchasable = True
template.salable = True
template.consumable = True
template.product_type_printery = 'papel'
#template.list_price = Decimal('0.05')
#template.cost_price = Decimal('0.08')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
# Rellenar campos especificos de PAPEL
template.genera_contribucion_marginal = False
template.width = float('72')
template.width_uom = unit_centimetro
template.height = float('102')
template.height_uom = unit_centimetro
template.weight = float('100')
template.weight_uom = unit_gramo
# uom information
# (ancho x alto x gramo) / 1000 = ratio
template.use_info_unit = True
template.info_unit = unit_kilogramo
#template.info_ratio = round(float(float('0.72') * float('1.02') * float('100') / 1000), 4)
template.info_list_price = Decimal('15')
template.cost_price = template.list_price
template.save()

# Crear producto Broche
template_broche = ProductTemplate()
template_broche.name = 'Broche Base'
template_broche.default_uom = unit
template_broche.type = 'goods'
template_broche.purchasable = True
template_broche.salable = True
template_broche.consumable = True
template_broche.product_type_printery = 'broche'
template_broche.list_price = Decimal('1')
template_broche.cost_price = Decimal('1')
template_broche.cost_price_method = 'fixed'
template_broche.account_expense = expense
template_broche.account_revenue = revenue
template_broche.genera_contribucion_marginal = False
template_broche.save()

# Crear producto Encuadernadora
template = ProductTemplate()
template.name = 'Encuadernado'
template.default_uom = unit_hour
template.type = 'service'
template.purchasable = False
template.salable = True
template.consumable = False
template.product_type_printery = 'maquina_encuadernacion'
template.list_price = Decimal('400')
template.cost_price = Decimal('400')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
template.genera_contribucion_marginal = True
template.velocidad_maq = Decimal('2000')
template.tiempo_arreglo = Decimal('0.5')
template.broche = template_broche.products[0]
template.save()

# Crear producto Doblado Diptico
template = ProductTemplate()
template.name = 'Doblado Diptico'
template.default_uom = unit_hour
template.type = 'service'
template.purchasable = False
template.salable = True
template.consumable = False
template.product_type_printery = 'maquina_doblado'
template.list_price = Decimal('120')
template.cost_price = Decimal('120')
template.cost_price_method = 'fixed'
template.account_expense = expense
template.account_revenue = revenue
template.genera_contribucion_marginal = True
template.velocidad_maq = Decimal('6000')
template.tiempo_arreglo = Decimal('0.5')
template.save()

# Create payment term:
PaymentTerm = Model.get('account.invoice.payment_term')
PaymentTermLine = Model.get('account.invoice.payment_term.line')

payment_term = PaymentTerm(name=u'30 días')
payment_term_line = PaymentTermLine(type='remainder', days=30)
payment_term.lines.append(payment_term_line)
payment_term.save()

payment_term = PaymentTerm(name=u'60 días')
payment_term_line = PaymentTermLine(type='remainder', days=60)
payment_term.lines.append(payment_term_line)
payment_term.save()

payment_term = PaymentTerm(name='Efectivo')
payment_term_line = PaymentTermLine(type='remainder', days=0)
payment_term.lines.append(payment_term_line)
payment_term.save()

# Create an Inventory:

config.user = admin_user.id
Inventory = Model.get('stock.inventory')
InventoryLine = Model.get('stock.inventory.line')
Location = Model.get('stock.location')
storage, = Location.find([
        ('code', '=', 'STO'),
        ])
inventory = Inventory()
inventory.location = storage
inventory.save()

#inventory_line = InventoryLine(product=product, inventory=inventory)
#inventory_line.quantity = 100.0
#inventory_line.expected_quantity = 0.0
#inventory.save()
#inventory_line.save()
#Inventory.confirm([inventory.id], config.context)
#inventory.state
print u'done Scenario Sale Printery Budget'
