"""导入导出 & 打印模板模型"""
from datetime import datetime
from extensions import db


class ExportTemplate(db.Model):
    """导出模板（支持多模板命名）"""
    __tablename__ = 'export_template'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(32), default='investment')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = db.relationship('ExportFieldConfig', backref='template', lazy='dynamic',
                              cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ExportFieldConfig(db.Model):
    """导出字段配置"""
    __tablename__ = 'export_field_config'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'field_key', name='uq_template_field'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('export_template.id'), nullable=False, default=1)
    field_key = db.Column(db.String(64), nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)
    column_width = db.Column(db.Integer, default=120)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_visible': self.is_visible,
            'is_custom': self.is_custom,
            'column_width': self.column_width,
            'sort_order': self.sort_order
        }


class ImportFieldConfig(db.Model):
    """导入字段配置（导入模板的列定义）"""
    __tablename__ = 'import_field_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class ExportFieldConfigActivity(db.Model):
    """招商动态导出字段配置"""
    __tablename__ = 'export_field_config_activity'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    column_width = db.Column(db.Integer, default=120)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_visible': self.is_visible,
            'column_width': self.column_width,
            'sort_order': self.sort_order
        }


class PrintTemplate(db.Model):
    """打印模板"""
    __tablename__ = 'print_template'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(32), default='investment')  # 'investment' | 'construction'
    paper_size = db.Column(db.String(20), default='A4')          # A4 | A3 | Letter
    orientation = db.Column(db.String(10), default='landscape')   # portrait | landscape
    font_family = db.Column(db.String(64), default='微软雅黑')
    font_size = db.Column(db.Integer, default=10)
    title_font_family = db.Column(db.String(64), default='微软雅黑')
    title_font_size = db.Column(db.Integer, default=14)
    table_header_font_family = db.Column(db.String(64), default='微软雅黑')
    table_header_font_size = db.Column(db.Integer, default=10)
    cell_font_family = db.Column(db.String(64), default='微软雅黑')
    cell_font_size = db.Column(db.Integer, default=10)
    header_font_size = db.Column(db.Integer, default=12)
    margin_top = db.Column(db.Float, default=0.5)                 # inches
    margin_bottom = db.Column(db.Float, default=0.5)
    margin_left = db.Column(db.Float, default=0.4)
    margin_right = db.Column(db.Float, default=0.4)
    show_page_number = db.Column(db.Boolean, default=True)
    show_print_meta = db.Column(db.Boolean, default=True)
    sub_title_font_size = db.Column(db.Integer, default=12)
    title_bold = db.Column(db.Boolean, default=True)
    subtitle_bold = db.Column(db.Boolean, default=True)
    border_style = db.Column(db.String(20), default='all')        # 'all' | 'none'
    group_by = db.Column(db.String(64), default='')
    template_file = db.Column(db.String(512), default='')
    data_start_row = db.Column(db.Integer, default=3)
    header_row = db.Column(db.Integer, default=2)
    title_row = db.Column(db.Integer, default=1)
    has_group_title = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = db.relationship('PrintFieldConfig', backref='template', lazy='dynamic',
                             cascade='all, delete-orphan')
    mappings = db.relationship('TemplateFieldMapping', backref='template', lazy='dynamic',
                               cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'entity_type': self.entity_type,
            'paper_size': self.paper_size,
            'orientation': self.orientation,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'title_font_family': self.title_font_family,
            'title_font_size': self.title_font_size,
            'table_header_font_family': self.table_header_font_family,
            'table_header_font_size': self.table_header_font_size,
            'cell_font_family': self.cell_font_family,
            'cell_font_size': self.cell_font_size,
            'header_font_size': self.header_font_size,
            'margin_top': self.margin_top,
            'margin_bottom': self.margin_bottom,
            'margin_left': self.margin_left,
            'margin_right': self.margin_right,
            'show_page_number': self.show_page_number,
            'show_print_meta': self.show_print_meta,
            'sub_title_font_size': self.sub_title_font_size,
            'title_bold': self.title_bold,
            'subtitle_bold': self.subtitle_bold,
            'border_style': self.border_style,
            'group_by': self.group_by,
            'template_file': self.template_file,
            'data_start_row': self.data_start_row,
            'header_row': self.header_row,
            'title_row': self.title_row,
            'has_group_title': self.has_group_title,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PrintFieldConfig(db.Model):
    """打印字段配置"""
    __tablename__ = 'print_field_config'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'field_key', name='uq_print_template_field'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('print_template.id'), nullable=False)
    field_key = db.Column(db.String(64), nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)
    column_width = db.Column(db.Integer, default=120)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_visible': self.is_visible,
            'is_custom': self.is_custom,
            'column_width': self.column_width,
            'sort_order': self.sort_order
        }


class TemplateFieldMapping(db.Model):
    """模板列→系统字段映射（上传 .xlsx 模板后自动解析列标题）"""
    __tablename__ = 'template_field_mapping'
    __table_args__ = (
        db.UniqueConstraint('template_id', 'column_letter', name='uq_template_column'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('print_template.id'), nullable=False)
    column_letter = db.Column(db.String(4), nullable=False)          # Excel 列字母: A, B, ... AA
    column_header = db.Column(db.String(255), default='')            # 模板中读到的列标题原文
    field_key = db.Column(db.String(64), default='')                 # 映射的系统字段 key（空=未映射）
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'template_id': self.template_id,
            'column_letter': self.column_letter,
            'column_header': self.column_header,
            'field_key': self.field_key,
            'sort_order': self.sort_order,
        }


class ImportFieldConfigActivity(db.Model):
    """招商动态导入字段配置"""
    __tablename__ = 'import_field_config_activity'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class ImportFieldConfigDemand(db.Model):
    """企业诉求导入字段配置"""
    __tablename__ = 'import_field_config_demand'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class ImportFieldConfigConstruction(db.Model):
    """在建项目导入字段配置"""
    __tablename__ = 'import_field_config_construction'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }


class ImportFieldConfigWorkProgress(db.Model):
    """工作进展导入字段配置"""
    __tablename__ = 'import_field_config_work_progress'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    field_key = db.Column(db.String(64), unique=True, nullable=False)
    field_label = db.Column(db.String(128), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'field_key': self.field_key,
            'field_label': self.field_label,
            'is_enabled': self.is_enabled,
            'is_required': self.is_required,
            'sort_order': self.sort_order
        }
