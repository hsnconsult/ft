# -*- coding: utf-8 -*-

import datetime
import math
import odoo.addons.decimal_precision as dp
import os
import ssl
import sys
import time
# from ftplib import FTP
# from ftplib import FTP_TLS
# import pysftp
# import zipfile
from itertools import islice
from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.osv import osv
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, float_compare, pycompat
from odoo.tools.float_utils import float_round as round

from .amount_to_text_fr import amount_to_text_fr


class IwelDelfi(models.Model):
    _name = "iwel.delfi"
    _description = "Donnees DELFI"

    delfi = fields.Char('Code Delfi')
    codep = fields.Char('Code produit')
    barcode = fields.Char('Code barre')
    libelle = fields.Char('Libellé')
    fournisseur = fields.Char('Fournisseur')
    reffour = fields.Char('Référence fournisseur')
    stock = fields.Float('Stock')
    pvente = fields.Float('Prix de vente')
    rayon = fields.Char('Rayon')
    famille = fields.Char('Sous rayon')
    pachat = fields.Float('Prix achat')
    type = fields.Char('Type')
    name = fields.Char("Name", compute='get_name')

    @api.depends('delfi', 'libelle')
    def get_name(self):
        for r in self:
            r.name = "%s-%s" % (r.delfi or "Delfi", r.libelle or "")


class paramftp(models.Model):
    _name = "iwel.paramftp"
    _description = "Parametres du FTP"

    serveur = fields.Char(string='Serveur FTP')
    user = fields.Char(string='Utilisateur FTP')
    password = fields.Char(string='Mot de passe FTP')
    repiwel = fields.Char(string='Répertoire IWEL')
    repentree = fields.Char(string='Entree des fichiers')
    reparchives = fields.Char(string='Archives des fichiers')

    name = fields.Char("Name", compute='get_name')

    @api.depends('serveur')
    def get_name(self):
        for r in self:
            r.name = r.serveur or "Ftp"


class Table(models.Model):
    _name = "iwel.table"
    _description = "Tables IWEL"

    def get_nbchamp(self):
        for record in self:
            record.nbchamp = len(self.env['iwel.champ'].search([('idtable', '=', record.id)]))

    active = fields.Boolean("Active", default=True)
    name = fields.Char(string='Nom')
    table = fields.Char(string='Table')
    mode = fields.Selection([('importer', 'Importer'), ('exporter', 'Exporter')], 'Mode')
    nb = fields.Integer('Nombre opérations')
    periodicite = fields.Selection(
        [('jour', 'Journalier'), ('semaine', 'Hebdomadaire'), ('mois', 'Mensuel'), ('trimestre', 'Trimestriel')],
        'Périodicité')
    sequence = fields.Integer('Sequence')
    nbchamp = fields.Integer('Nombre de champs')
    positionref = fields.Integer(string='Position ref unique')
    positionname = fields.Integer(string='Position name')
    champoblig = fields.Text(String='Champs obligatoires')
    valdef = fields.Text(String='Valeurs des champs')
    nbaj = fields.Integer(String='Nombre de champs ajoutés')
    ligne_champs = fields.One2many('iwel.champ', 'idtable', 'Champ')


class Champ(models.Model):
    _name = "iwel.champ"
    _description = "Champs IWEL"

    idtable = fields.Many2one('iwel.table', string='Table')
    name = fields.Char(string='Nom')
    numcol = fields.Integer(string='Num Colonne')
    nomcol = fields.Integer(string='Nom Colonne')
    position = fields.Integer(string='Position')
    longueur = fields.Integer(string='Longueur')
    libelle = fields.Char(string='Libellé')
    format = fields.Char(string='Format')
    description = fields.Text(string='Description')
    odoo = fields.Char('Champ ODOO')


class ProductCategory(models.Model):
    _name = "product.category"
    _inherit = "product.category"

    code = fields.Char('Code catégorie')
    codeparent = fields.Char('Code Parent catégorie')
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    _sql_constraints = [
        ('codeunique', 'unique(code,codeparent)', 'Existe deja')
    ]


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.depends('ligne_gencod.c1')
    def get_barcode(self):
        for record in self:
            barcode2 = barcode3 = ''
            i = 1
            for recordfil in record.ligne_gencod:
                if i == 1:
                    barcode2 = recordfil.c1
                if i == 2:
                    barcode3 = recordfil.c1
                i = i + 1
            record.barcode2 = barcode2
            record.barcode3 = barcode3

    @api.depends('idfamille')
    def get_rayon(self):
        for record in self:
            record.idrayon = record.idfamille.idrayon.id

    def myround(self, x, base=5):
        return base * round(x / base, 0)

    def majprix(self):
        company_id = self.env.user.company_id
        for record in self:
            if record.frais is not None and record.frais != 0 and record.coeff is not None and record.coeff != 0:
                record.cout = record.prixbase_dj * (1 + record.frais / 100)
                record.list_price = self.myround(record.prixbase_dj * (1 + record.frais / 100) * record.coeff, 5)
                record.marge = round((self.myround(record.prixbase_dj * (1 + record.frais / 100) * record.coeff, 5) - (
                        record.prixbase_dj * (1 + record.frais / 100))) / (
                                             record.prixbase_dj * (1 + record.frais / 100)), 2) * 100

    @api.depends('list_price', 'standard_price')
    def get_marge(self):
        for record in self:
            if self.standard_price != 0:
                record.margeb = round(((self.list_price - self.standard_price) / self.standard_price) * 100, 2)
            else:
                record.margeb = 0

    c1 = fields.Char('Date de création')
    c2 = fields.Char('Date de modification')
    c3 = fields.Char('Code article Domaxel')
    refuniq = fields.Char('Code article Domaxel')
    c4 = fields.Char('Code fournisseur Domaxel')
    c5 = fields.Char('Département d\'activité')
    c6 = fields.Char('Référence article fournisseur')
    c7 = fields.Char('Code marque propre')
    c8 = fields.Char('Marque propre')
    c9 = fields.Char('Langue')
    c10 = fields.Char('Libellé caisse')
    c11 = fields.Char('Désignation article')
    c12 = fields.Char('Libellé long')
    c13 = fields.Char('Code TVA')
    c14 = fields.Char('Quantité minimum de commande')
    c15 = fields.Char('Première quantité pour remise')
    c16 = fields.Char('Coefficient de 1ere remise')
    c17 = fields.Char('Deuxième quantité pour remise')
    c18 = fields.Char('Coefficient de 2eme remise')
    c19 = fields.Char('Troisième quantité pour remise')
    c20 = fields.Char('Coefficient de 3eme remise')
    c21 = fields.Char('Unité de prix à la cession')
    c22 = fields.Char('Nombre de sous unité consommateur dans l’article')
    c23 = fields.Char('EAN 13')
    c24 = fields.Char('Code secteur')
    c25 = fields.Char('Code nomenclature Domaxel')
    c26 = fields.Char('Assortiment mini (NIV GAMME)')
    c27 = fields.Char('Assortiment normal (NIV GAMME)')
    c28 = fields.Char('Assortiment élargi (NIV GAMME)')
    c29 = fields.Char('Assortiment complémentaire 1')
    c30 = fields.Char('Assortiment complémentaire 2')
    c31 = fields.Char('Code Etiquette EAN')
    c32 = fields.Char('Image')
    c33 = fields.Char('Code modèle')
    c34 = fields.Char('Unité légale')
    c35 = fields.Char('Mesure de l’article exprimé en unité légale')
    c36 = fields.Char('Pays d’origine ')
    c37 = fields.Char('Poids brut de l’unité de vente')
    c38 = fields.Char('Délai de garantie')
    c39 = fields.Char('Circuit d’approvisionnement')
    c40 = fields.Char('Article permanent')
    c41 = fields.Char('Exclusif à une enseigne')
    c42 = fields.Char('Enseigne')
    c43 = fields.Char('Statut de l’article')
    c44 = fields.Char('Article de substitution')
    c45 = fields.Char('Code Univers')
    c46 = fields.Char('Date visibilité article')
    c47 = fields.Char('Transmission aux adhérents')
    c48 = fields.Char('Ancienne unité de prix')
    c49 = fields.Char('Art à délai de liv. supp')
    c50 = fields.Char('Saison. Non commandable')
    c51 = fields.Char('Filler')
    c52 = fields.Char('Type PSG')
    c53 = fields.Char('Rayon')
    c54 = fields.Char('Famille')
    c55 = fields.Char('Sous-famille')
    c56 = fields.Char('Segment')
    c57 = fields.Char('Sous-segment')
    c58 = fields.Char('Date de fin de vie')
    c59 = fields.Char('Type de remplacement')
    c60 = fields.Char('Code eco produit')
    c61 = fields.Char('Stock non garanti (STKNG)')
    c62 = fields.Char('N° fournisseur réel')
    c63 = fields.Char('Volume')
    c64 = fields.Char('ag.codelmf_generalites à destination du WS OMS')
    idfamille = fields.Many2one('iwel.wnomfam', string='Famille')
    idrayon = fields.Many2one('iwel.wnomray', compute='get_rayon', store=True)
    idfournisseur = fields.Many2one('iwel.fournisseur', string='Fournisseur Weldom')
    barcode2 = fields.Char('Code barre 2')
    barcode3 = fields.Char('Code barre 3')
    prixbase = fields.Float('Prix de base(Euro)')
    prixbase_dj = fields.Float('Prix de base(WELDOM)')
    prixbase_brico = fields.Float('Prix de base(BRICO)')
    cout = fields.Float('Coût Weldom')
    marge = fields.Float('Marge(%)')
    margeb = fields.Float('Marge(%)', compute='get_marge')
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits=dp.get_precision('Product Price'),
        help="Price at which the product is sold to customers.", track_visibility='onchange')

    ligne_gencod = fields.One2many('iwel.wgencode', 'idarticle', 'gencode')
    ligne_promo = fields.One2many('iwel.wpart', 'idarticle', 'promo')
    ligne_promod = fields.One2many('iwel.wpdirect', 'idarticle', 'promod')
    ligne_fonc = fields.One2many('iwel.wlibplus', 'idarticle', 'fonction')
    ligne_tarif = fields.One2many('iwel.wtarif', 'idarticle', 'tarifs')
    codeimport = fields.Char('Code import')
    codedel = fields.Char('Code Del')
    stockdelfi = fields.Float('Stock Delfi')
    _sql_constraints = [
        ('reference unique', 'unique(refuniq)', 'Existe deja')
    ]


class IwelTypesoffres(models.Model):
    _name = "iwel.typesoffres"
    _description = "iwel.typesoffres"

    c1 = fields.Char('Numéro enregistrement')
    c2 = fields.Char('Code offre')
    c3 = fields.Char('Libelle offre')
    c4 = fields.Char('Libelle court offre')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c3')
    def get_name(self):
        for r in self:
            r.name = r.c3 or "Type offre"


class IwelArticlesoffres(models.Model):
    _name = "iwel.articlesoffres"
    _description = "iwel.articlesoffres"

    idarticle = fields.Many2one('product.template', string='Code article')
    idtype = fields.Many2one('iwel.typesoffres', string='Type offre')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Code offre')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Offre article"


class IwelWassorti(models.Model):
    _name = "iwel.wassorti"
    _description = "iwel.wassorti"

    c1 = fields.Char('Code assortissement')
    c2 = fields.Char('Libellé assortissement')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Assortissement"


class IwelWassorart(models.Model):
    _name = "iwel.wassorart"
    _description = "Assortissement articles"

    idarticle = fields.Many2one('product.template', string='Code article')
    c1 = fields.Char('Code article')
    c2 = fields.Many2one('iwel.assorti', string='Code assortissement')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2.name or "")
            else:
                r.name = "Assortissement"


class IwelWassorcli(models.Model):
    _name = "iwel.wassorcli"
    _description = "Assortissement clients"

    idassort = fields.Many2one('iwel.assorti', string='Code assortissement')
    c1 = fields.Char('Code client')
    c2 = fields.Char('Code assortissement')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Assortissement"


class IwelWgencode(models.Model):
    _name = "iwel.wgencode"
    _description = "GEN Code"

    c1 = fields.Char('GEN CODE EAN')
    c2 = fields.Char('Code article')
    c3 = fields.Char('Statut')
    idarticle = fields.Many2one('product.template', string='Article')
    idproduit = fields.Many2one('product.product', string='Produit')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Wgencode"


class IwelWlibelleversion(models.Model):
    _name = "iwel.wlibelleversion"
    _description = "Entete de promo"

    c1 = fields.Char('Code Theme Promo')
    c2 = fields.Char('Code Version')
    c3 = fields.Char('Libellé Version')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c3')
    def get_name(self):
        for r in self:
            if r.c1 and r.c3:
                r.name = "%s / %s" % (r.c1 or "", r.c3 or "")
            else:
                r.name = "Entête promo"


class IwelWpart(models.Model):
    _name = "iwel.wpart"
    _description = "Promo article"

    idarticle = fields.Many2one('product.template', string='Article')
    idtheme = fields.Many2one('iwel.libelleversion', string='Code Thème promo')
    c1 = fields.Char('Article')
    c2 = fields.Char('Code Thème promo')
    c3 = fields.Char('Nature article')
    c4 = fields.Char('Libellé')
    c5 = fields.Char('Logo de marque')
    c6 = fields.Char('Norme NF')
    c7 = fields.Char('Picto Garantie')
    c8 = fields.Char('Num Page Catalogue')
    c9 = fields.Char('Num version catalogue')
    c10 = fields.Char('Code de désactivation')
    c11 = fields.Char('Quantités préconisées M1')
    c12 = fields.Char('Quantités préconisées M2')
    c13 = fields.Char('Quantités préconisées M3')
    c14 = fields.Char('Minimum vente')
    c15 = fields.Char('Code devise')
    c16 = fields.Char('Prix engagement')
    c17 = fields.Char('Prix Hors engagement')
    c18 = fields.Char('PVI TTC')
    c19 = fields.Char('PVI unité légale')
    c20 = fields.Char('PVI unité légale en Euro')
    c21 = fields.Char('Qté 1 donnant une remise')
    c22 = fields.Char('Coefficient 1 de remise')
    c23 = fields.Char('Qté 2 donnant une remise')
    c24 = fields.Char('Coefficient 2 de remise')
    c25 = fields.Char('Qté 3 donnant une remise')
    c26 = fields.Char('Coefficient 3 de remise')
    c27 = fields.Char('Prix permanent')
    c28 = fields.Char('col 28')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Promo article"


class IwelWpdirect(models.Model):
    _name = "iwel.wpdirect"
    _description = "Promo direct"

    idarticle = fields.Many2one('product.template', string='Article')
    idcollection = fields.Many2one('iwel.wpent', string='Numero Collection')
    c1 = fields.Char('Numero Collection')
    c2 = fields.Char('Code Article')
    c3 = fields.Many2one('res.partner', string='Fournisseur')
    c4 = fields.Char('Quantité 1')
    c5 = fields.Char('Prix 1')
    c6 = fields.Char('Quantité 2')
    c7 = fields.Char('Prix 2')
    c8 = fields.Char('Quantité 3')
    c9 = fields.Char('Prix 3')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s - %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Promo direct"


class IwelWpent(models.Model):
    _name = "iwel.wpent"
    _description = "Entete promo"

    idtheme = fields.Many2one('iwel.libelleversion', string='Code Thème promo')
    c1 = fields.Char('Code Thème promo')
    c2 = fields.Char('Libellé')
    c3 = fields.Char('Nature thème')
    c4 = fields.Char('Début prépromo')
    c5 = fields.Char('Pin prépromo')
    c6 = fields.Char('Début Promo')
    c7 = fields.Char('Fin Promo')
    c8 = fields.Char('Début vente magasin')
    c9 = fields.Char('Fin vente magasin')
    c10 = fields.Char('Nombre de livraisons')
    c11 = fields.Char('Date de livraison 1')
    c12 = fields.Char('Date de livraison 2')
    c13 = fields.Char('Date de livraison 3')
    c14 = fields.Char('Date de livraison 4')
    c15 = fields.Char('Date de livraison 5')
    c16 = fields.Char('Date de livraison 6')
    c17 = fields.Char('Tous clients')
    c18 = fields.Char('Condition reglement Eng')
    c19 = fields.Char('Date reglement Eng')
    c20 = fields.Char('Condition reglement Ass')
    c21 = fields.Char('Date reglement Ass')
    c22 = fields.Char('Remise packaging')
    c23 = fields.Char('Num version et page')
    c24 = fields.Char('Gestion du Réassort')
    c25 = fields.Char('Filler')
    c26 = fields.Char('Date règlement1')
    c27 = fields.Char('Date règlement2')
    c28 = fields.Char('Date règlement3')
    c29 = fields.Char('Date règlement4')
    c30 = fields.Char('Date règlement5')
    c31 = fields.Char('Date règlement6')
    c32 = fields.Char('Type promo')
    c33 = fields.Char('col 33')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Entete promo"


class IwelWlibplus(models.Model):
    _name = "iwel.wlibplus"
    _description = "Desc fonctionnelle"

    idarticle = fields.Many2one('product.template', string='Article')
    c1 = fields.Char('Code Article')
    c2 = fields.Char('Code Langue')
    c3 = fields.Char('Num Ligne')
    c4 = fields.Char('Description Fonctionnelle')
    c5 = fields.Char('col 5')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Desc fonctionnel"


class IwelWlibtec(models.Model):
    _name = "iwel.wlibtec"
    _description = "Desc technique"

    idarticle = fields.Many2one('product.template', string='Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Code Langue')
    c3 = fields.Char('Num Ligne')
    c4 = fields.Char('Description Technique')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Description technique"


class IwelWmarpro(models.Model):
    _name = "iwel.wmarpro"
    _description = "Marque"

    c1 = fields.Char('Code')
    c2 = fields.Char('Marque')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Marque"


class IwelWnomray(models.Model):
    _name = "iwel.wnomray"
    _description = "Rayon"
    _rec_name = "c2"

    def majprix(self):
        for record in self:
            for recordfam in record.ligne_famille:
                for recordart in recordfam.ligne_article:
                    # MAJ FRAIS
                    if recordart.frais == 0:
                        if recordfam.frais == 0:
                            if record.frais != 0:
                                recordart.standart_price = recordart.prixbase * (1 + record.frais / 100)
                        else:
                            recordart.standart_price = recordart.prixbase * (1 + recordfam.frais / 100)
                    else:
                        recordart.standart_price = recordart.prixbase * (1 + recordart.frais / 100)
                    # MAJ COEFF
                    if recordart.coeff == 0:
                        if recordfam.coeff == 0:
                            if record.coeff != 0:
                                recordart.list_price = recordart.prixbase * (1 + record.frais / 100) * record.coeff
                        else:
                            recordart.list_price = recordart.prixbase * (1 + recordfam.frais / 100) * recordfam.coeff
                    else:
                        recordart.list_price = recordart.prixbase * (1 + recordart.frais / 100) * recordart.coeff

    c1 = fields.Char('Code')
    c2 = fields.Char('Nom rayon', required=1)
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    ligne_famille = fields.One2many('iwel.wnomfam', 'idrayon', 'Familles')


class IwelWnomfam(models.Model):
    _name = "iwel.wnomfam"
    _description = "Famille"
    _rec_name = "c3"

    idrayon = fields.Many2one('iwel.wnomray', string='Rayon')
    c1 = fields.Char('Code Rayon')
    c2 = fields.Char('Code')
    c3 = fields.Char('Nom famille', required=1)
    frais = fields.Float('Frais(%)')
    coeff = fields.Float('Coeff(%)')
    ligne_article = fields.One2many('product.template', 'idfamille', 'Articles')


class IwelWtarif(models.Model):
    _name = "iwel.wtarif"
    _description = "Tarif"

    idarticle = fields.Many2one('product.template', string='Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Zone de prix')
    c3 = fields.Char('Devise prix de base')
    c4 = fields.Char('Prix achat')
    c5 = fields.Char('Devise prix de cession')
    c6 = fields.Char('Prix de cession')
    c7 = fields.Char('PVI TTC')
    c8 = fields.Char('PVI TTC EURO')
    c9 = fields.Char('Date Application')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Tarif"


class IwelWtarifspec(models.Model):
    _name = "iwel.wtarifspec"
    _description = "Tarif spec"

    idarticle = fields.Many2one('product.template', string='Article')
    c1 = fields.Char('Code article')
    c2 = fields.Char('Zone de prix')
    c3 = fields.Char('Devise prix de base')
    c4 = fields.Char('Prix achat')
    c5 = fields.Char('Devise prix de cession')
    c6 = fields.Char('Prix de cession')
    c7 = fields.Char('PVI TTC')
    c8 = fields.Char('PVI TTC EURO')
    c9 = fields.Char('Date Application')
    c10 = fields.Char('Code tarif')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c10', 'c2')
    def get_name(self):
        for r in self:
            if r.c10 and r.c2:
                r.name = "%s / %s" % (r.c10 or "", r.c2 or "")
            else:
                r.name = "Tarif spec"


class IwelWtarifspecmq(models.Model):
    _name = "iwel.wtarifspecmq"
    _description = "Tarif spec marque"

    c1 = fields.Char('Code contremarque')
    c2 = fields.Char('Code tarif')

    name = fields.Char("Name", compute='get_name')

    @api.depends('c1', 'c2')
    def get_name(self):
        for r in self:
            if r.c1 and r.c2:
                r.name = "%s / %s" % (r.c1 or "", r.c2 or "")
            else:
                r.name = "Tarif spec marque"


class iwel_fournisseur(models.Model):
    _name = "iwel.fournisseur"
    _description = "Fournisseurs Weldom"
    _rec_name = "c3"

    name = fields.Char("Name", compute='get_name')

    def get_name(self):
        for r in self:
            r.name = r.c4

    c1 = fields.Char('Code fournisseur')
    c2 = fields.Char('Forme juridique')
    c3 = fields.Char('Raison sociale', required=1)
    c4 = fields.Char('Dénomination', required=1)
    c5 = fields.Char('Code secteur')
    c6 = fields.Char('Adresse1')
    c7 = fields.Char('Adresse2')
    c8 = fields.Char('Adresse3')
    c9 = fields.Char('Ville')
    c10 = fields.Char('Téléphone')
    c11 = fields.Char('Télécopie')
    c12 = fields.Char('Email')
    c13 = fields.Char('Identifiant CEE')
    c14 = fields.Char('Début contrat')
    c15 = fields.Char('Fin contrat')
    c16 = fields.Char('Dernière BFA')
    c17 = fields.Char('Minimum commande')
    c18 = fields.Char('Delai livraison')
    c19 = fields.Char('Tarif base')
    c20 = fields.Char('Remise globale')
    c21 = fields.Char('Filler')
    c22 = fields.Char('Longeur')
    c23 = fields.Char('col23')


class iwel_gestfichier(models.Model):
    _name = "iwel.gestfichier"
    _description = 'Gestion des fichiers'

    def imp_fichierspecial(self):
        idext = self.env['ir.model.data']
        imp = self.env['iwel.table'].search([('mode', '=', 'importer'), ('nb', '!=', '0')])
        for record in imp:
            # fichier = "C:\IWEL\ENTREE\\"+record.name
            fichier = record.name
            cr = open(fichier, "r", encoding='cp437')
            nbl = 0
            for ligne in cr:
                text = ligne.replace("'", " ").replace("\n", "").split(';')
                if record.positionname != 0:
                    text.extend([text[record.positionname], text[record.positionref]])
                else:
                    text.append(text[record.positionref])
                if len(record.valdef) != 0:
                    recup = record.valdef.split(',')
                    text.extend(recup)
                col = []
                for i in range(1, record.nbchamp + 1):
                    colname = "c" + str(i)
                    col.append(colname)
                if len(record.champoblig.strip()) != 0:
                    recup2 = record.champoblig.split(',')
                    col.extend(recup2)
                colonnes = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp + record.nbaj:
                        colonnes = colonnes + str(c) + ')'
                    else:
                        colonnes = colonnes + str(c) + ','
                    inc = inc + 1
                valeurs = "("
                inc = 1

                colonnex = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp + record.nbaj:
                        colonnex = colonnex + "EXCLUDED." + str(c) + ')'
                    else:
                        colonnex = colonnex + "EXCLUDED." + str(c) + ','
                    inc = inc + 1
                valeurs = "("
                inc = 1
                # raise UserError(col)
                for v in text:
                    if inc == record.nbchamp + record.nbaj:
                        valeurs = valeurs + str(v) + ')'
                    else:
                        valeurs = valeurs + str(v) + ','
                    inc = inc + 1
                requete = "INSERT INTO " + record.table + colonnes + " VALUES" + str(
                    tuple(text)) + " ON CONFLICT (refuniq) DO UPDATE SET " + colonnes + "=" + colonnex
                nbl = nbl + 1
                res = self.env.cr.execute(requete)

    def imp_fichier(self):
        idext = self.env['ir.model.data']
        imp = self.env['iwel.table'].search([('mode', '=', 'importer'), ('nb', '=', '5')])
        for record in imp:
            # fichier = record.name
            fichier = "/home/odoo/iwel/entree/" + record.name
            cr = open(fichier, "r", encoding='cp437')
            print("Importation okay")
            nbl = 0
            reqdel = "DELETE FROM " + record.table
            res2 = self.env.cr.execute(reqdel)
            for ligne in cr:
                text = ligne.replace("'", " ").replace("\n", "").split(';')
                col = []
                for i in range(1, record.nbchamp + 1):
                    colname = "c" + str(i)
                    col.append(colname)
                colonnes = "("
                inc = 1
                for c in col:
                    if inc == record.nbchamp + record.nbaj:
                        colonnes = colonnes + str(c) + ')'
                    else:
                        colonnes = colonnes + str(c) + ','
                    inc = inc + 1
                valeurs = "("
                inc = 1
                for v in text:
                    if inc == record.nbchamp + record.nbaj:
                        valeurs = valeurs + str(v) + ')'
                    else:
                        valeurs = valeurs + str(v) + ','
                    inc = inc + 1
                requete = "INSERT INTO " + record.table + colonnes + " VALUES" + str(tuple(text))
                nbl = nbl + 1
                res1 = self.env.cr.execute(requete)
        self.majtable()
        self.maj_prixdep()

    def majtable(self):
        req1 = "UPDATE iwel_wgencode A SET idarticle = P.id FROM product_template P WHERE A.c2 = P.c3"
        req2 = "UPDATE iwel_wpart A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req3 = "UPDATE iwel_wpdirect A SET idarticle = P.id FROM product_template P WHERE A.c2 = P.c3"
        req4 = "UPDATE iwel_wlibplus A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req5 = "UPDATE iwel_wtarif A SET idarticle = P.id FROM product_template P WHERE A.c1 = P.c3"
        req6 = "UPDATE product_template SET default_code = c3 where c3 is not null"
        req7 = "UPDATE product_product p SET barcode = t.c23 FROM product_template t where p.product_tmpl_id=t.id and t.c23 is not null"
        req8 = "UPDATE product_template SET weight = c37::float where c37 is not null"
        req9 = "UPDATE product_template SET volume = c63::float where c63 is not null"
        req10 = "UPDATE iwel_wnomfam f SET idrayon = r.id FROM iwel_wnomray r WHERE f.c1 = r.c1"
        req11 = "UPDATE product_template p SET idfamille = f.id FROM iwel_wnomfam f WHERE p.c54 = f.c2 AND idfamille is null"
        req12 = "UPDATE product_template p SET prixbase = t.c6::float/100 FROM iwel_wtarif t WHERE t.idarticle = p.id and prixbase is null"
        req13 = "update product_template set sale_line_warn = 'no-message' where sale_line_warn = '1'"
        req14 = "update product_template set purchase_line_warn = 'no-message' where purchase_line_warn = '1'"
        req15 = "update product_template set tracking = 'none' where tracking = '1'"
        reqq = "update product_template p set idrayon = f.idrayon from iwel_wnomfam f where p.idfamille = f.id AND p.idrayon is null"
        self.env.cr.execute(req1)
        self.env.cr.execute(req2)
        self.env.cr.execute(req3)
        self.env.cr.execute(req4)
        self.env.cr.execute(req5)
        self.env.cr.execute(req6)
        self.env.cr.execute(req7)
        self.env.cr.execute(req8)
        self.env.cr.execute(req9)
        self.env.cr.execute(req10)
        self.env.cr.execute(req11)
        self.env.cr.execute(req12)
        self.env.cr.execute(req13)
        self.env.cr.execute(req14)
        self.env.cr.execute(req15)
        self.env.cr.execute(reqq)

    name = fields.Char('Reference')

    def maj_prixdep(self):
        req20 = "UPDATE product_template SET prixbase_dj = prixbase * (SELECT tauxdevise FROM res_company WHERE name LIKE 'bricodiscount.dj') WHERE c3 is not null AND prixbase is null"
        req21 = "UPDATE product_template SET cout = prixbase * (1+(SELECT frais FROM res_company WHERE name LIKE 'bricodiscount.dj')/100) WHERE c3 is not null AND prixbase is null"
        req22 = "UPDATE product_template SET list_price = round((cout*(SELECT coeff FROM res_company WHERE name LIKE 'bricodiscount.dj'))/5)*5 WHERE c3 is not null AND prixbase is null"
        self.env.cr.execute(req20)
        self.env.cr.execute(req21)
        self.env.cr.execute(req22)

    def maj_prix(self):
        reqp1 = "UPDATE product_template p SET prixbase = t.c6::float/100 FROM iwel_wtarif t WHERE t.idarticle = p.id"
        reqp2 = "UPDATE product_template SET prixbase_dj = prixbase * (SELECT tauxdevise FROM res_company WHERE name LIKE 'bricodiscount.dj')"
        reqp3 = "UPDATE product_template SET cout = prixbase * (1+(SELECT frais FROM res_company WHERE name LIKE 'bricodiscount.dj')/100)"
        reqp4 = "UPDATE product_template SET list_price = round((cout*(SELECT coeff FROM res_company WHERE name LIKE 'bricodiscount.dj'))/5)*5 WHERE c3 is not null"
        self.env.cr.execute(reqp1)
        self.env.cr.execute(reqp2)
        self.env.cr.execute(reqp3)
        # self.env.cr.execute(reqp4)

    def reception(self):
        pass
        # repentree = "/home/odoo/iwel/entree"
        # repentreeserv = "/home/brico/entree"
        # reparchiveserv = "/home/brico/archives"
        # cnopts = pysftp.CnOpts()
        # cnopts.hostkeys = None
        # with pysftp.Connection('159.89.226.75', username='brico', password='brico', cnopts=cnopts) as sftp:
        #     with sftp.cd('/home/brico/archives'): # temporarily chdir to allcode
        #         fichiers_archives = [f for f in sftp.listdir() if f != "." and f != ".."]
        #
        #     print('fichierrrsss archives ===+>' , fichiers_archives)
        #
        #     with sftp.cd('/home/brico/entree'):  # temporarily chdir to allcode
        #         os.chdir(repentree)
        #         fichiers = [f for f in sftp.listdir() if f != "." and f != ".."]
        #         print('fichierrrsss===+>' , fichiers)
        #
        #         for fichier in fichiers:
        #             nomfichier = repentreeserv + "/" + fichier
        #             nomarchive = reparchiveserv + "/" + fichier
        #             sftp.get(nomfichier)  # get a remote file
        #             print('=======================================================================')
        #             print('FICHIER', fichier)
        #             print('nom archive', nomarchive)
        #             print('nom fichier', nomfichier)
        #             print('==============================> SUCCESS <==============================')
        #             if fichier not in fichiers_archives:
        #                 sftp.rename(nomfichier, nomarchive)
        #             print('============================== THANK LORD ====================================')
        #             if '.zip' in fichier:
        #                 self.unzip(fichier, '/home/odoo/iwel/entree')

    def reception_local(self):
        pass
        # repentree = "C:\IWEL\ENTREE"
        # repentreeserv = "/home/brico/entree"
        # reparchiveserv = "/home/brico/archives"
        # cnopts = pysftp.CnOpts()
        # cnopts.hostkeys = None
        # with pysftp.Connection('159.89.226.75', username='brico', password='brico', cnopts=cnopts) as sftp:
        #     with sftp.cd('/home/brico/entree'):  # temporarily chdir to allcode
        #         os.chdir(repentree)
        #         fichiers = [f for f in sftp.listdir() if f != "." and f != ".."]
        #         for fichier in fichiers:
        #             nomfichier = repentreeserv + "/" + fichier
        #             nomarchive = reparchiveserv + "/" + fichier
        #             sftp.get(nomfichier)  # get a remote file
        #             sftp.rename(nomfichier, nomarchive)
        #             if '.zip' in fichier:
        #                 self.unzip(fichier, 'C:\IWEL\ENTREE')

    def unzip(self, fichier, rep):
        pass

    def maj_cost(self):
        product = self.env['product.template'].search([('codeimport', '=like', '%D%'), ('active', '=', False)])
        # raise UserError(len(product))
        for record in product:
            record.standard_price = record.prixbase_brico * 1.2705

    def imp_bla(self):
        repentree = "/home/odoo/iwel/entree"
        # repentree = "C:\IWEL\ENTREEBL"
        os.chdir(repentree)
        fichierzip = [f for f in os.listdir() if '.zip' in f or '.ZIP' in f]
        for fichier in fichierzip:
            self.unzip(fichier, repentree)
        fichiersbla = [f for f in os.listdir() if 'BLA' in f]
        for fichierbla in fichiersbla:
            cr = open(fichierbla, "r", encoding='cp437')
            recep = self.env['iwel.reception']
            recepligne = []
            for ligne in cr:
                text = ligne.replace("'", " ").replace("\n", "").split(';')
                vals = {
                    'c1': text[0],
                    'c2': text[1],
                    'c3': text[2],
                    'c4': text[3],
                    'c5': text[4],
                    'c6': text[5],
                    'c7': text[6],
                    'c8': text[7],
                    'c9': text[8],
                    'c10': text[9],
                    'c11': text[10],
                    'c12': text[11],
                    'c13': text[12],
                    'c14': text[13],
                    'c15': text[14],
                    'c16': text[15],
                    'c17': text[16],
                    'c18': text[17],
                    'c19': text[18],
                    'c20': text[19],
                    'c21': text[20],
                    'c22': text[21],
                    'c23': text[22],
                    'c24': text[23],
                    'c25': text[24],
                    'c26': text[25],
                }
                recepligne.append((0, False, vals))
            recepc = recep.create({'fichier': fichierbla})
            # raise UserError(recepc)
            for record in recepc:
                record.write({'ligne_reception': recepligne})


class Company(models.Model):
    _name = "res.company"
    _description = 'Companies'
    _inherit = "res.company"

    def amount_in_words(self, amount):
        return amount_to_text_fr(amount, 'F Dj')

    deciwel = fields.Integer(string='Décimal WELDOM')
    tauxdevise = fields.Integer(string='Taux devise')
    coeff = fields.Float(string='Coefficient WELDOM')
    frais = fields.Float(string='Frais WELDOM')
    # Parametre des etiquettes
    margeh = fields.Float('Marge Haut')
    margeg = fields.Float('Marge Gauche')
    hauteur = fields.Float('Hauteur')
    hauteurgencode = fields.Float('Hauteur Gencode')
    longeurgencode = fields.Float('Longeur Gencode')
    iev = fields.Float('Interligne vertical')
    ieh = fields.Float('Interligne horizontal')
    nbh = fields.Integer('Nombre Horizontal')
    nbv = fields.Integer('Nombre Vertical')
    sequencecom = fields.Many2one('ir.sequence', string='Sequence commandes Weldom')


class iwel_etiquette(models.Model):
    _name = "iwel.etiquette"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Etiquettes IWEL"

    @api.depends('ligne_etiquette')
    def get_nbetiquette(self):
        for record in self:
            record.nb = len(record.ligne_etiquette)

    date = fields.Date('Date de création')
    nb = fields.Integer('Nombre', compute='get_nbetiquette')
    ligne_etiquette = fields.One2many('iwel.ligneetiquette', 'idetiquette', 'Etiquettes')
    name = fields.Char("Name", compute='get_name', store=1)

    @api.model
    def create(self, vals):
        res = super(iwel_etiquette, self).create(vals)
        print('====')
        print(res.id)
        res.name = "Etiquette " + str(res.id)
        return res

    def split_etiquettes(self):
        print("=========++++>", self.ligne_etiquette)
        number = int(self.nb / 4)
        rest = self.nb % 4
        print(rest)
        print(number)
        splits = [4 for i in range(0, number)]
        if rest > 0:
            splits += [rest]

        print('==========>', splits)
        Inputt = iter(self.ligne_etiquette)
        Output = [list(islice(Inputt, elem))
                  for elem in splits]
        print("=========================++++++>", Output)
        return Output

    def get_name(self):
        for r in self:
            r.name = "Etiquette " + str(r.id)


class iwel_ligneetiquette(models.Model):
    _name = "iwel.ligneetiquette"
    _description = "Lignes etiquettes"

    @api.onchange('barcode')
    def barcode_onchange(self):
        if self.barcode:
            print('=========================')
            print(self.barcode)
            print('=========================')

            product = self.env['product.template'].search([('barcode', '=', self.barcode)])
            product_p = self.env['product.product'].search([('barcode', '=', self.barcode)])

            print('============================================')
            print(product)
            print(product_p)
            print('===========================================')

            if product:
                self.nomp = product[0].name
                self.codep = product[0].default_code
                self.codef = product[0].c4
                self.date = product[0].create_date
                self.prix = product[0].list_price
                self.currency_id = product[0].currency_id.id

    idetiquette = fields.Many2one('iwel.etiquette', string='Etiquette')
    barcode = fields.Char('Code barre')
    nomp = fields.Char('Nom produit')
    codep = fields.Char('Code Produit')
    codef = fields.Char('Code Fourn.')
    date = fields.Date('Date')
    prix = fields.Float('Prix', digits=(16, 0))
    currency_id = fields.Many2one('res.currency', string='Devise')

    name = fields.Char("Name", compute='get_name')

    def get_name(self):
        for r in self:
            r.name = "Ligne etiquette %s" % (r.id)
