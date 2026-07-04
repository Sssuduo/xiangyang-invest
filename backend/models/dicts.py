"""字典模型：所有业务字典表"""
from extensions import db


class FollowStatusDict(db.Model):
    """跟进状态字典"""
    __tablename__ = 'follow_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }


class MeetingStatusDict(db.Model):
    """上会状态字典"""
    __tablename__ = 'meeting_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }


class OrganizationDict(db.Model):
    """单位字典（推介单位 & 包保单位共用）"""
    __tablename__ = 'organization_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class ProjectTypeDict(db.Model):
    """项目类型字典"""
    __tablename__ = 'project_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class ProjectTagDict(db.Model):
    """项目标签字典"""
    __tablename__ = 'project_tag_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class ActivityTagDict(db.Model):
    """动态标签字典"""
    __tablename__ = 'activity_tag_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class DemandTypeDict(db.Model):
    """诉求类型字典（支持两级：parent_code 为空则为一级）"""
    __tablename__ = 'demand_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    parent_code = db.Column(db.String(32), default='')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'parent_code': self.parent_code or '',
            'sort_order': self.sort_order, 'is_active': self.is_active
        }

    @staticmethod
    def build_display_name_map():
        """构建 code → display_name 映射（子级显示为 一级：二级）"""
        all_items = DemandTypeDict.query.all()
        name_map = {d.code: d.name for d in all_items}
        result = {}
        for d in all_items:
            if d.parent_code and d.parent_code in name_map:
                result[d.code] = f'{name_map[d.parent_code]}：{d.name}'
            else:
                result[d.code] = d.name
        return result

    @staticmethod
    def resolve_display_names(codes_str, separator='、'):
        """将逗号分隔的编码字符串解析为显示名称（用于多选值）"""
        if not codes_str:
            return ''
        name_map = DemandTypeDict.build_display_name_map()
        names = []
        for code in codes_str.split(','):
            code = code.strip()
            if code:
                names.append(name_map.get(code, code))
        return separator.join(names) if names else ''


class ConstructionProjectTypeDict(db.Model):
    """在建项目类型字典"""
    __tablename__ = 'construction_project_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class DispatchStatusDict(db.Model):
    """调度状态字典"""
    __tablename__ = 'dispatch_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class IssueTypeDict(db.Model):
    """存在问题类型字典"""
    __tablename__ = 'issue_type_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'sort_order': self.sort_order, 'is_active': self.is_active
        }


class ResolutionStatusDict(db.Model):
    """解决状态字典"""
    __tablename__ = 'resolution_status_dict'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    display_color = db.Column(db.String(32), default='#909399')
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'display_color': self.display_color, 'sort_order': self.sort_order,
            'is_active': self.is_active
        }
