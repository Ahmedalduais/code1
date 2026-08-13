# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class UniLibraryBorrow(models.Model):
    """الاستعارة — تسجيل إعارة كتاب لمستعير.

    يدعم النموذج استعارات للطلاب وأعضاء هيئة التدريس والموظفين
    والأطراف الخارجية (شركاء res.partner) مع تتبع تواريخ الاستعارة
    والإرجاع المتوقع والفعلي وحساب الغرامات تلقائياً عند التأخير.

    يوفّر النموذج:
        * توليد رقم تسلسلي تلقائي LBR/%(year)s/00000
        * حساب ``is_overdue`` و ``days_overdue`` و ``fine_amount`` تلقائياً
        * دعم تجديد الاستعارة حتى ``max_renewals`` مرات
        * إنشاء غرامة تلقائية عند الإرجاع المتأخر عبر ``uni.library.fine``
    """
    _name = 'uni.library.borrow'
    _description = 'Library Borrow Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'borrow_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default='New', tracking=True, index=True,
        help='Unique sequence reference of the borrow record.')
    code = fields.Char(
        string='Code', copy=False, tracking=True, index=True,
        help='Optional secondary code for manual lookups.')

    # ------------------------------------------------------------------
    # Book & Borrower
    # ------------------------------------------------------------------
    book_id = fields.Many2one(
        'uni.library.book', string='Book', required=True, ondelete='restrict',
        tracking=True, index=True,
        help='Book being borrowed.')
    borrower_type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('external', 'External'),
    ], string='Borrower Type', required=True, default='student',
        tracking=True, index=True,
        help='Category of borrower.')
    student_name = fields.Char(
        string='Student Name', tracking=True,
        help='Name of the student borrowing the book (free text — the '
             'library module does not depend on university_student).')
    student_code = fields.Char(
        string='Student Code', tracking=True, index=True,
        help='Optional student identifier code (e.g. student number).')
    faculty_name = fields.Char(
        string='Faculty Name', tracking=True,
        help='Name of the faculty member borrowing the book (free text '
             '— the library module does not depend on university_faculty).')
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        ondelete='restrict',
        help='Staff employee borrowing the book.')
    partner_id = fields.Many2one(
        'res.partner', string='External Partner',
        ondelete='restrict',
        help='External borrower (e.g. visiting scholar, library member).')
    borrower_name = fields.Char(
        string='Borrower Name', compute='_compute_borrower_name',
        store=True, tracking=True,
        help='Display name of the borrower (computed from the related '
             'record).')

    # NOTE: The library module is intentionally decoupled from
    # ``university_student`` and ``university_faculty`` per the official
    # architecture specification. Student/faculty borrowers are recorded
    # as free-text Char fields (``student_name`` / ``faculty_name``) to
    # preserve the dependency contract.

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    borrow_date = fields.Date(
        string='Borrow Date', required=True,
        default=fields.Date.context_today, tracking=True,
        help='Date the book was handed to the borrower.')
    due_date = fields.Date(
        string='Due Date', required=True, tracking=True,
        help='Date by which the book must be returned.')
    return_date = fields.Date(
        string='Planned Return Date', tracking=True,
        help='Optional planned return date set by the librarian.')
    actual_return_date = fields.Date(
        string='Actual Return Date', tracking=True,
        help='Date the book was actually returned.')

    # ------------------------------------------------------------------
    # Overdue & fines
    # ------------------------------------------------------------------
    is_overdue = fields.Boolean(
        string='Is Overdue', compute='_compute_overdue', store=True,
        tracking=True, index=True,
        help='True if the book is past its due date and not yet returned.')
    days_overdue = fields.Integer(
        string='Days Overdue', compute='_compute_days_overdue', store=True,
        help='Number of days the book is late (0 if not overdue).')
    fine_amount = fields.Float(
        string='Fine Amount', compute='_compute_fine', store=True,
        digits=(16, 2),
        help='Calculated fine based on overdue days and the configured '
             'daily rate.')
    fine_currency_id = fields.Many2one(
        'res.currency', string='Fine Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency of the calculated fine.')
    fine_paid = fields.Boolean(
        string='Fine Paid', default=False, tracking=True,
        help='True if the fine was settled.')
    fine_id = fields.Many2one(
        'uni.library.fine', string='Fine Record', copy=False,
        ondelete='set null',
        help='Linked fine record if one was created.')

    # ------------------------------------------------------------------
    # Renewal
    # ------------------------------------------------------------------
    renewed_count = fields.Integer(
        string='Renewals', default=0, tracking=True,
        help='Number of times the borrow has been renewed.')
    max_renewals = fields.Integer(
        string='Max Renewals', default=2, required=True,
        help='Maximum number of renewals allowed.')

    # ------------------------------------------------------------------
    # State & notes
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='borrowed', required=True,
        tracking=True, index=True, group_expand='_group_expand_states',
        help='Lifecycle state of the borrow record.')
    notes = fields.Text(
        string='Notes', translate=True,
        help='Internal notes about this borrow.')

    _sql_constraints = [
        ('unique_borrow_name', 'unique(name)',
         'Borrow reference must be unique!'),
    ]

    # ------------------------------------------------------------------
    # Create — auto sequence
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate the sequence reference for each new borrow."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uni.library.borrow') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('borrower_type', 'student_name', 'faculty_name',
                 'employee_id', 'partner_id')
    def _compute_borrower_name(self):
        """Resolve the borrower display name based on borrower type."""
        for rec in self:
            if rec.borrower_type == 'student' and rec.student_name:
                rec.borrower_name = rec.student_name
            elif rec.borrower_type == 'faculty' and rec.faculty_name:
                rec.borrower_name = rec.faculty_name
            elif rec.borrower_type == 'staff' and rec.employee_id:
                rec.borrower_name = rec.employee_id.display_name
            elif rec.borrower_type == 'external' and rec.partner_id:
                rec.borrower_name = rec.partner_id.display_name
            else:
                rec.borrower_name = False

    @api.depends('due_date', 'actual_return_date', 'state')
    def _compute_overdue(self):
        """A borrow is overdue if past due date and not returned/cancelled."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state in ('returned', 'cancelled', 'lost'):
                rec.is_overdue = False
            elif rec.due_date and today > rec.due_date:
                rec.is_overdue = True
            else:
                rec.is_overdue = False

    @api.depends('due_date', 'actual_return_date', 'state', 'is_overdue')
    def _compute_days_overdue(self):
        """Compute the number of overdue days.

        Uses actual_return_date if returned late, otherwise uses today.
        """
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.is_overdue and rec.state != 'overdue':
                rec.days_overdue = 0
                continue
            reference_date = rec.actual_return_date or today
            if rec.due_date and reference_date > rec.due_date:
                rec.days_overdue = (reference_date - rec.due_date).days
            else:
                rec.days_overdue = 0

    @api.depends('days_overdue', 'is_overdue', 'state')
    def _compute_fine(self):
        """Compute the fine amount based on overdue days.

        Uses the system parameter ``library.fine_per_day`` (default 1.0)
        in the company currency.
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'library.fine_per_day', default='1.0')
        try:
            rate = float(param)
        except (TypeError, ValueError):
            rate = 1.0
        for rec in self:
            if rec.days_overdue > 0 and rec.state in ('borrowed', 'overdue'):
                rec.fine_amount = rec.days_overdue * rate
            elif rec.days_overdue > 0 and rec.state == 'returned':
                # Keep fine calculated even after return (for settlement)
                rec.fine_amount = rec.days_overdue * rate
            else:
                rec.fine_amount = 0.0

    # ------------------------------------------------------------------
    # Group expand
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_states(self, states, domain, order):
        """Return all known state keys for grouping."""
        return [key for key, _label in self._fields['state'].selection]

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def action_return(self):
        """Mark the book as returned and create a fine if overdue."""
        Fine = self.env['uni.library.fine']
        for rec in self:
            if rec.state not in ('borrowed', 'overdue'):
                raise UserError(_(
                    "Borrow %(name)s cannot be returned from state "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            today = fields.Date.context_today(rec)
            rec.actual_return_date = today
            rec.state = 'returned'
            # Recompute overdue / days / fine before creating fine record
            rec._compute_overdue()
            rec._compute_days_overdue()
            rec._compute_fine()
            if rec.days_overdue > 0 and rec.fine_amount > 0 \
                    and not rec.fine_id:
                fine = Fine.create({
                    'borrow_id': rec.id,
                    'fine_type': 'overdue',
                    'amount': rec.fine_amount,
                    'currency_id': rec.fine_currency_id.id,
                    'issue_date': today,
                    'description': _(
                        'Automatic overdue fine for borrow %s.') % rec.name,
                })
                rec.fine_id = fine.id
            rec.message_post(body=_(
                "Book returned on %(date)s.") % {'date': today})

    def action_renew(self):
        """Renew the borrow by extending the due date by 14 days."""
        default_extension = 14
        for rec in self:
            if rec.state not in ('borrowed', 'overdue'):
                raise UserError(_(
                    "Cannot renew borrow %(name)s in state %(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            if rec.renewed_count >= rec.max_renewals:
                raise UserError(_(
                    "Maximum renewals (%(max)d) reached for borrow "
                    "%(name)s.") % {
                    'max': rec.max_renewals,
                    'name': rec.name,
                })
            base_date = rec.due_date or fields.Date.context_today(rec)
            rec.due_date = base_date + fields.timedelta(days=default_extension)
            rec.renewed_count += 1
            if rec.state == 'overdue':
                rec.state = 'borrowed'
            rec.message_post(body=_(
                "Borrow renewed (%(n)d/%(max)d). New due date: %(date)s.") % {
                'n': rec.renewed_count,
                'max': rec.max_renewals,
                'date': rec.due_date,
            })

    def action_cancel(self):
        """Cancel the borrow record."""
        for rec in self:
            if rec.state == 'returned':
                raise UserError(_(
                    "Cannot cancel a returned borrow (%s).") % rec.name)
            rec.state = 'cancelled'
            rec.message_post(body=_("Borrow cancelled."))

    def action_mark_lost(self):
        """Mark the borrowed book as lost."""
        for rec in self:
            if rec.state not in ('borrowed', 'overdue'):
                raise UserError(_(
                    "Cannot mark borrow %(name)s as lost from state "
                    "%(state)s.") % {
                    'name': rec.name,
                    'state': rec.state,
                })
            rec.state = 'lost'
            # Mark the book itself as lost
            if rec.book_id:
                rec.book_id.state = 'lost'
            rec.message_post(body=_(
                "Book marked as LOST for borrow %s.") % rec.name)

    def action_view_fine(self):
        """Open the linked fine record if it exists."""
        self.ensure_one()
        if not self.fine_id:
            raise UserError(_("No fine linked to this borrow."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fine'),
            'res_model': 'uni.library.fine',
            'res_id': self.fine_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('borrow_date', 'due_date')
    def _check_due_after_borrow(self):
        """Due date must be on or after the borrow date."""
        for rec in self:
            if rec.borrow_date and rec.due_date \
                    and rec.due_date < rec.borrow_date:
                raise ValidationError(_(
                    "Due date (%(due)s) cannot be before borrow date "
                    "(%(borrow)s) for borrow %(name)s.") % {
                    'due': rec.due_date,
                    'borrow': rec.borrow_date,
                    'name': rec.name,
                })

    @api.constrains('actual_return_date', 'borrow_date')
    def _check_return_after_borrow(self):
        """Actual return date must be on or after the borrow date."""
        for rec in self:
            if rec.actual_return_date and rec.borrow_date \
                    and rec.actual_return_date < rec.borrow_date:
                raise ValidationError(_(
                    "Actual return date (%(ret)s) cannot be before borrow "
                    "date (%(borrow)s) for borrow %(name)s.") % {
                    'ret': rec.actual_return_date,
                    'borrow': rec.borrow_date,
                    'name': rec.name,
                })

    @api.constrains('borrower_type', 'student_name', 'faculty_name',
                    'employee_id', 'partner_id')
    def _check_borrower_consistency(self):
        """The chosen borrower record must match the borrower type."""
        for rec in self:
            if rec.borrower_type == 'student' and not rec.student_name:
                raise ValidationError(_(
                    "Student borrower name is required for borrow %s.") % rec.name)
            if rec.borrower_type == 'faculty' and not rec.faculty_name:
                raise ValidationError(_(
                    "Faculty borrower name is required for borrow %s.") % rec.name)
            if rec.borrower_type == 'staff' and not rec.employee_id:
                raise ValidationError(_(
                    "Employee borrower is required for borrow %s.") % rec.name)
            if rec.borrower_type == 'external' and not rec.partner_id:
                raise ValidationError(_(
                    "External partner is required for borrow %s.") % rec.name)

    @api.constrains('renewed_count', 'max_renewals')
    def _check_renewal_limit(self):
        """Renewed count cannot exceed max renewals."""
        for rec in self:
            if rec.renewed_count > rec.max_renewals:
                raise ValidationError(_(
                    "Renewal count (%(n)d) cannot exceed maximum "
                    "(%(max)d) for borrow %(name)s.") % {
                    'n': rec.renewed_count,
                    'max': rec.max_renewals,
                    'name': rec.name,
                })
