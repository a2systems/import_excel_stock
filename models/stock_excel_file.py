# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unicodedata import name
from dateutil.relativedelta import relativedelta
from datetime import date,datetime,timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import ValidationError

import base64
import csv
from io import StringIO

import xlrd

class StockExcelFile(models.Model):
    _name = 'stock.excel.file'
    _inherit = ['mail.thread','mail.activity.mixin']  
    _description = "Importacion Excel"

    name = fields.Char('Nombre',tracking=True)
    excel_file = fields.Binary('Archivo Excel',tracking=True,
        states={"draft": [("readonly", False)]})
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("done", "Procesado"),
        ],
        default="draft",
        tracking=True
    )
    date = fields.Date('Fecha',default=fields.Date.today())
    location_id = fields.Many2one('stock.location',string='Ubicacion',domain="[('usage','=','internal')]")
    product_ids = fields.One2many(comodel_name='product.template',inverse_name='stock_file_id',string='Productos')
    lot_ids = fields.One2many(comodel_name='stock.lot',inverse_name='stock_file_id',string='Nros de Serie')
    move_ids = fields.One2many(comodel_name='stock.move',inverse_name='stock_file_id',string='Stock Moves')
    move_line_ids = fields.One2many(comodel_name='stock.move.line',inverse_name='stock_file_id',string='Stock Move Lines')

    def btn_process_file(self):
        self.ensure_one()
        if not self.excel_file:
            raise ValidationError('Por favor ingrese el archivo')
        if not self.location_id:
            raise ValidationError('Por favor ingrese la ubicacion')
        wb = xlrd.open_workbook(file_contents = base64.decodebytes(self.excel_file))
        sheet = wb.sheets()[0]
        for row in range(sheet.nrows):
            if row < 1:
                continue
            prod = None
            serial = None
            qty = 0
            for col in range(sheet.ncols):
                cell_value = sheet.cell(row,col).value
                if col == 0:
                    prod = cell_value
                elif col == 1:
                    serial = cell_value
                else:
                    qty = cell_value
            if prod and qty > 0:
                product_id = self.env['product.template'].search([('default_code','=',prod.strip())],limit=1)
                if not product_id:
                    vals_prod = {
                            'name': prod.strip(),
                            'default_code': prod.strip(),
                            'stock_file_id': self.id,
                            'type': 'product',
                            'tracking': 'lot',
                            }
                    product_id = self.env['product.template'].create(vals_prod)
                prod_id = self.env['product.product'].search([('product_tmpl_id','=',product_id.id)],limit=1)
                lot_id = None
                if serial and product_id:
                    lot_id = self.env['stock.lot'].search([('name','=',serial.strip()),('product_id','=',prod_id.id)],limit=1)
                    if not lot_id:
                        vals_lot = {
                            'name': serial.strip(),
                            'ref': serial.strip(),
                            'product_id': prod_id.id,
                            'stock_file_id': self.id,
                            }
                        lot_id = self.env['stock.lot'].create(vals_lot)
                if not lot_id:
                    quants = self.env['stock.quant'].search([('location_id','=',self.location_id.id),('product_id','=',prod_id.id)])
                else:
                    quants = self.env['stock.quant'].search([
                        ('location_id','=',self.location_id.id),
                        ('product_id','=',prod_id.id),
                        ('lot_id','=',lot_id.id),
                        ])
                quantity = sum(quants.mapped('quantity'))
                decrease = False
                if qty > quantity:
                    diff = qty - quantity
                else:
                    diff = quantity - qty
                    decrease = True
                location_adj = self.env['stock.location'].search([('complete_name','=','Virtual Locations/Inventory adjustment')],limit=1)
                if not location_adj:
                    raise ValidationError('Scrap location no definida')
                if not decrease:
                    src_location = location_adj.id
                    dest_location = self.location_id.id
                else:
                    dest_location = location_adj.id
                    src_location = self.location_id.id
                if diff > 0:
                    vals_move = {
                            'stock_file_id': self.id,
                            'product_uom': prod_id.uom_id.id,
                            'product_id': prod_id.id,
                            'name': 'Actualizacion inventario %s %s'%(self.name,prod_id.display_name),
                            'company_id': 1,
                            'state': 'draft',
                            'is_inventory': True,
                            'location_id': src_location,
                            'location_dest_id': dest_location,
                            'product_uom_qty': diff
                            }
                    move_id = self.env['stock.move'].create(vals_move)
                    vals_move_line = {
                            'stock_file_id': self.id,
                            'move_id': move_id.id,
                            'product_uom_id': prod_id.uom_id.id,
                            'product_id': prod_id.id,
                            'lot_id': lot_id.id,
                            'company_id': 1,
                            'state': 'draft',
                            'is_inventory': True,
                            'location_id': src_location,
                            'location_dest_id': dest_location,
                            'qty_done': diff
                            }
                    move_line_id = self.env['stock.move.line'].create(vals_move_line)
                    move_id._action_done()

