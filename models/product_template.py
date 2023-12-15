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

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_file_id = fields.Many2one('stock.excel.file',string='Archivo de Excel')
