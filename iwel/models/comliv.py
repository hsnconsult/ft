# -*- coding: utf-8 -*-

# from ftplib import FTP
# from ftplib import FTP_TLS
# import pysftp
# import zipfile
import os
import ssl
import sys
import time
import math
import datetime
import pprint
import odoo.addons.decimal_precision as dp

from odoo import tools
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, float_compare, pycompat
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from odoo.osv import osv


class IwelReception(models.Model):
    _name = "iwel.reception"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "receptions IWEL"
    _rec_name = 'fichier'

    name = fields.Char('Name', copy=False, compute='_get_name')

    @api.depends('numbl')
    def _get_name(self):
        for r in self:
            r.name = r.numbl or 'Reception %s' % r.id

    @api.onchange('codebare')
    def affichep(self):
        return {'domain': {'ligne_reception': [('c11', '=', self.codebare)]}}

    def miseenstock(self):
        transint = \
            self.env['stock.picking'].search([('picking_type_id.code', '=', 'internal'), ('origin', '=', self.numbl)])[
                1]
        # raise UserError(transint)
        for record in transint.move_lines:
            record.quantity_done = record.reserved_availability
        transint.button_validate()
        self.write({'state': 'enstock'})

    def ajustrecep(self):
        for record in self.ligne_reception:
            record.qterecue = record.c14

    def startrecep(self):
        # Contrôle
        if self.env['iwel.reception'].search(
                [('id', '!=', self.id), ('state', 'not in', ('attente', 'enstock', 'termine'))]):
            raise UserError("Il y a une réception en cours ou dans la zone INPUT")
            self.numbl = self.ligne_reception[0].c2
        # self.write({'state':'encours','numbl':'BL N°'+self.numbl})
        # self.write({'state':'termine'})
        idpartenaire = self.env['res.partner'].search([('name', '=', 'WELDOM')])[0]
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', self.env.user.company_id.id)])[:1]
        pick = self.env['stock.picking']
        valspick = {
            'picking_type_id': picking_type_id.id,
            'partner_id': idpartenaire.id,
            'date': self.datereception,
            # 'origin': 'BL N°'+self.numbl,
            'origin': 'BL N°' + self.ligne_reception[0].c2,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'location_id': idpartenaire.property_stock_supplier.id,
            'company_id': self.env.user.company_id.id,
        }
        pick = pick.create(valspick)
        self.write({'state': 'encours', 'idpicking': pick.id})

    def validetout(self):
        for record in self.ligne_reception:
            if record.state == 'nonvalid':
                record.validecom()
        self.idpicking.button_validate()
        self.write({'state': 'termine'})

    @api.depends('ligne_reception.state')
    def get_total(self):
        for record in self:
            record.nb = len(self.env['iwel.lignereception'].search([('idreception', '=', record.id)]))
            record.nbvalide = len(
                self.env['iwel.lignereception'].search([('idreception', '=', record.id), ('state', '=', 'valide')]))
            record.nbnonvalide = len(
                self.env['iwel.lignereception'].search([('idreception', '=', record.id), ('state', '=', 'nonvalid')]))

    fichier = fields.Char('Fichier')
    numbl = fields.Char('N° BL')
    datereception = fields.Date('Date de réception')
    codebare = fields.Char('Code Barre')
    nbvalide = fields.Integer('Total validé', compute='get_total')
    nbnonvalide = fields.Integer('Total non validé', compute='get_total')
    nb = fields.Integer('Total', compute='get_total')
    idpicking = fields.Many2one('stock.picking', string='Réception')
    ligne_reception = fields.One2many('iwel.lignereception', 'idreception', 'receptions')
    state = fields.Selection(
        [('attente', 'En attente'), ('encours', 'En cours'), ('termine', 'Terminée'), ('enstock', 'En stock')], 'Etat',
        track_visibility='onchange', default='attente')

    def create_purchase_order(self):
        # requests = self.env['sochepress.customer.request'].search([('invoice_ids', 'in', self.id)])
        # lines = []
        # for request in requests:
        #     lines += [line.id for line in request.request_line_ids]
        # print(lines)
        to_invoice = self.ligne_reception.filtered(lambda l: not l.is_invoiced)
        if to_invoice:
            action = self.env.ref('iwel.create_po_action').read()[0]
            action['domain'] = [('id', 'in', to_invoice.ids)]

            return action


    po_ids = fields.One2many('purchase.order', 'idreception', string="Orders")
    nb_pos = fields.Integer("Orders count", compute='compute_pos')

    @api.depends('po_ids')
    def compute_pos(self):
        for r in self:
            r.nb_pos = len(r.po_ids)

    def see_purchase_orders(self):
        # requests = self.env['sochepress.customer.request'].search([('invoice_ids', 'in', self.id)])
        # lines = []
        # for request in requests:
        #     lines += [line.id for line in request.request_line_ids]
        # print(lines)
        if not self.datereception:
            raise UserError("Please fill the reception date")

        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if self.nb_pos > 1:
            action['domain'] = [('id', 'in', self.po_ids.ids)]
            action['views'] = [(self.env.ref('purchase.purchase_order_tree').id, 'tree'),
                               (self.env.ref('purchase.purchase_order_form').id, 'form')]
        elif self.nb_pos == 1:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.po_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action


class IwelLignereception(models.Model):
    _name = "iwel.lignereception"
    _description = "Lignes de reception IWEL"

    is_invoiced=fields.Boolean("Is invoiced")
    name = fields.Char('Name', copy=False, compute='_get_name')

    def _get_name(self):
        for r in self:
            r.name = r.c10 or 'Ligne reception %s' % r.id


    @api.depends('c14', 'c13', 'qterecue', 'endommage')
    def get_ecart(self):
        for record in self:
            record.ecart = record.c14 - record.qterecue - record.endommage
            record.ecartcom = record.c13 - record.qterecue - record.endommage

    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        idtemp = self.env['product.template'].search([('c3', '=', self.c9)])[0]
        idproduit = self.env['product.product'].search([('product_tmpl_id', '=', idtemp.id)])[0]
        # raise UserError(idproduit.id)
        idpartenaire = self.env['res.partner'].search([('name', '=', 'WELDOM')])[0]
        picking_type_id = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', self.env.user.company_id.id)])[:1]
        self.ensure_one()
        res = []
        uom = self.env['product.template'].search([('c3', '=', self.c9)])[0].uom_po_id
        template = {
            'name': self.c2 or '',
            'product_id': idproduit.id,
            'product_uom': uom.id,
            'product_uom_qty': self.qterecue,
            'date': self.idreception.datereception,
            'date_expected': self.idreception.datereception,
            'location_id': idpartenaire.property_stock_supplier.id,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'picking_id': picking.id,
            'state': 'draft',
            'company_id': self.env.user.company_id.id,
            'picking_type_id': picking_type_id.id,
            'origin': 'BL N°' + self.c2,
            'route_ids': picking_type_id.warehouse_id and [
                (6, 0, [x.id for x in picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': picking_type_id.warehouse_id.id,
            'quantity_done': self.qterecue,
            'reserved_availability': self.qterecue,
        }
        res.append(template)
        return res

    def _create_stock_moves(self, picking):
        values = []
        for line in self:
            for val in line._prepare_stock_moves(picking):
                values.append(val)
        return self.env['stock.move'].create(values)

    def validecom(self):
        moves = self._create_stock_moves(self.idreception.idpicking)
        moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
        seq = 0
        for move in sorted(moves, key=lambda move: move.date_expected):
            seq += 5
            move.sequence = seq
        moves._action_assign()
        self.write({'state': 'valide', 'idpicking': self.idreception.idpicking.id})

    idreception = fields.Many2one('iwel.reception', string='reception')
    idpicking = fields.Many2one('stock.picking', string='Réception')
    idtransfert = fields.Many2one('stock.picking', string='Transfert')
    c1 = fields.Char('Contremarque')
    c2 = fields.Char('N° BL')
    c3 = fields.Char('Date BL')
    c4 = fields.Char('Ref Commande')
    c5 = fields.Char('N° ligne')
    c6 = fields.Char('Code fournisseur')
    c7 = fields.Char('Nom fournisseur')
    c8 = fields.Char('Ref fournisseur')
    c9 = fields.Char('Code article')
    c10 = fields.Char('Désignation')
    c11 = fields.Char('Code EAN13')
    c12 = fields.Char('Devise')
    c13 = fields.Float('Qte Com')
    c14 = fields.Float('Qte BL')
    qterecue = fields.Float('Qte reçue Bon')
    endommage = fields.Float('Qte reçue End', default=0.0)
    ecart = fields.Float('Ec.Liv', compute='get_ecart', store=True)
    ecartcom = fields.Float('Ec.Com', compute='get_ecart', store=True)
    comment = fields.Selection([('manquant', 'MQ'), ('endom', 'ENDM')], 'Motif')
    c15 = fields.Char('Prix achat')
    c16 = fields.Char('PVI')
    c17 = fields.Char('Code TVA')
    c18 = fields.Char('Code Promo')
    c19 = fields.Char('Code catalogue')
    c20 = fields.Char('Unité de prix')
    c21 = fields.Char('Unité emballage')
    c22 = fields.Char('Disponibilité commande')
    c23 = fields.Char('Secteur achat')
    c24 = fields.Char('Nomenclature')
    c25 = fields.Char('Colis')
    c26 = fields.Char('Filler')
    state = fields.Selection([('valide', 'Validée'), ('nonvalid', 'Non validé')], 'Etat', track_visibility='onchange',
                             default='nonvalid')

    def _prepare_purchase_order_data(self, reception):
        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the SO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        self.ensure_one()
        data = {}
        if reception:
            if not self.env['res.partner'].search([('name', '=', 'WELDOM')]):
                raise UserError("Please create the partner of the purchase")
            data = {
                'origin': reception.numbl,
                'partner_id': self.env['res.partner'].search([('name', '=', 'WELDOM')]).id,
                'date_order': reception.datereception,
                'date_planned': reception.datereception,
                'state': 'draft',
                'idreception': reception.id,
            }

        return data

    def _prepare_purchase_order_line_data(self, values):
        lines = []
        producttemplate = self.env['product.template']
        product = self.env['product.product']
        for val in values:
            idtemp = producttemplate.search([('refuniq', '=', val.c9)])
            if not idtemp:
                raise UserError("You have to specify the code of products")
            lines.append((0, 0, {
                'name': idtemp.name,
                'product_id': product.search([('product_tmpl_id', '=', idtemp.id)]).id,
                'product_uom': idtemp.uom_po_id.id,
                'price_unit': 0.0,
                'product_qty': val.c13,
                'idreception': val.id,
            }))
        return lines

    @api.model
    def action_create_po(self):
        po = self.env['purchase.order']
        pol = self.env['purchase.order.line']
        lignes = self.env['iwel.lignereception'].browse(self._context.get('active_ids', []))
        po_data = False
        if lignes:
            po_data = self._prepare_purchase_order_data(lignes[0].idreception)
        pol_datas = self._prepare_purchase_order_line_data(lignes)
        pprint.pprint(po_data)
        pprint.pprint(pol_datas)
        if len(po_data) > 0:
            po_data['order_line'] = pol_datas
            pprint.pprint(po_data)
            poid = po.create(po_data)
            if poid:
                for ligne in lignes:
                    ligne.is_invoiced = True
                if lignes and lignes[0].idreception:
                    reception = lignes[0].idreception
                    to_invoice = reception.ligne_reception.filtered(lambda l: not l.is_invoiced)
                    if len(to_invoice) == 0:
                        reception.state = 'termine'
                    else:
                        reception.state = 'encours'
            print(poid)
            action = self.env.ref('purchase.purchase_rfq').read()[0]
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = poid.id

        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action





class IwelCommande(models.Model):
    _name = "iwel.commande"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Commandes IWEL"

    @api.depends('ligne_commande.c1')
    def get_nbligne(self):
        for record in self:
            record.nbligne = len(record.ligne_commande)

    def validecommande(self):
        if self.nbligne <= 0:
            raise UserError('Aucune commande')
        for record in self.ligne_commande:
            if len(record.c1) == 0:
                raise UserError('Code article incorrect')
            if len(record.c2) != 13:
                raise UserError('Code barre incorrect')
            if len(record.c3) <= 0:
                raise UserError('Quantité incorrecte')
        company_id = self.env.user.company_id
        for com in self:
            if com.name == '':
                com.name = company_id.sequencecom.next_by_id()
        self.gen_file(self.name + '.txt')
        self.send_file(self.name + '.txt')
        self.write({'state': 'valide'})

    def gen_file(self, nomfichier):
        repsortie = "/home/odoo/iwel/sortie/"
        f = open(repsortie + nomfichier, "+w")
        nb = str(self.nbligne)
        md = str(self.date)
        f.write("%s;%s;%s;\n" % (nb.zfill(6), md.replace('-', ''), self.name))
        for record in self.ligne_commande:
            c1 = record.c1 if record.c1 else ''
            c2 = record.c2 if record.c2 else ''
            c3 = record.c3.zfill(5) if record.c3 else ''
            c4 = record.c4 if record.c4 else ''
            c5 = record.c5 if record.c5 else ''
            c6 = record.c6 if record.c6 else ''
            c7 = record.c7 if record.c7 else ''
            c8 = record.c8 if record.c8 else ''
            c9 = record.c9 if record.c9 else ''
            c10 = record.c10 if record.c10 else ''
            c11 = record.c11 if record.c11 else ''
            c12 = record.c112 if record.c12 else ''
            f.write("%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n" % (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12))
        f.close()

    def send_file(self, nomfichier):
        pass
        # repsortie = "/home/odoo/iwel/sortie/"
        # repsortieserv = "/home/brico/sortie"
        # cnopts = pysftp.CnOpts()
        # cnopts.hostkeys = None
        # with pysftp.Connection('159.89.226.75', username='brico', password='brico', cnopts=cnopts) as sftp:
        #     with sftp.cd('/home/brico/sortie'):  # temporarily chdir to allcode
        #         os.chdir(repsortie)
        #         nomfichier = repsortie + nomfichier
        #         sftp.put(nomfichier)

    nbligne = fields.Integer('Nombre de lignes', compute='get_nbligne', store=True)
    idfournisseur = fields.Many2one('iwel.fournisseur', string='Fournisseur')
    date = fields.Date('Date de création')
    name = fields.Char('Référence', copy=False, readonly=True, index=True)
    supcom = fields.Char('Supprimer commande')
    fichier = fields.Char('Fichier')
    ligne_commande = fields.One2many('iwel.lignecommande', 'idcommande', string='Commandes')
    state = fields.Selection([('nouveau', 'Nouvelle'), ('valide', 'Validée')], 'Etat', track_visibility='onchange',
                             default='nouveau')

    @api.model
    def create(self, values):
        res = super(IwelCommande, self).create(values)
        if res and not res.name:
            res.name = 'Commande ' + str(res.id)
        return res


class IwelLignecommande(models.Model):
    _name = "iwel.lignecommande"
    _description = "Lignes de reception IWEL"

    name = fields.Char('Nom', copy=False)

    @api.onchange('idarticle')
    def on_change_c1(self):
        self.c1 = self.idarticle.default_code
        self.c2 = self.idarticle.barcode
        self.c4 = self.idarticle.c6
        self.c5 = self.idarticle.name
        self.c9 = self.idarticle.c21
        self.c10 = self.idarticle.c21

    idcommande = fields.Many2one('iwel.commande', string='Commande')
    idarticle = fields.Many2one('product.template', string='Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Code barre')
    c3 = fields.Char('Quantité')
    c4 = fields.Char('Clé secondaire')
    c5 = fields.Char('Désignation')
    c6 = fields.Char('Code disponibilité')
    c7 = fields.Char('Quantité disponible')
    c8 = fields.Char('Notre prix')
    c9 = fields.Char('Unité de prix')
    c10 = fields.Char('Unité emballage min')
    c11 = fields.Char('Code article remplacecement')
    c12 = fields.Char('Notes')


class IwelComliv(models.Model):
    _name = "iwel.comliv"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Commandes receptions"

    nbgen = fields.Integer('Nombre')

