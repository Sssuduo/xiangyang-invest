"""模型聚合入口 —— 保持 from models import Xxx 完全兼容"""
from models.base import TimestampMixin
from models.auth import AdminUser, BusinessUser, Staff, ClientUser
from models.client_app import ClientChatSession, ClientChatMessage, ClientBrief, ClientBriefRead
from models.content import HomepageConfig, CarouselPage, ProvinceInfo, CityInfo, ContactInfo, PromoVideo
from models.ai import (LLMModel, QuickPrompt, KnowledgeEntry, KnowledgeDraft,
    KnowledgeUsageStat, KnowledgeEntryChangeLog, KnowledgeEntryHistory)
from models.dicts import (FollowStatusDict, MeetingStatusDict, OrganizationDict,
    ProjectTypeDict, DemandTypeDict, ProjectTagDict, ActivityTagDict,
    ConstructionProjectTypeDict, DispatchStatusDict, IssueTypeDict, ResolutionStatusDict)
from models.investment import (InvestmentProject, InvestmentLead, EnterpriseDemand,
    InvestmentActivity, ActivityLedger, ActivityDemandLink,
    LeadAssessmentSession, LeadAssessmentMessage)
from models.construction import ConstructionProject, WorkProgress, ProjectIssue, WorkRoadmapItem
from models.export_print import (ExportTemplate, ExportFieldConfig, ImportFieldConfig,
    ExportFieldConfigActivity, ImportFieldConfigActivity, ImportFieldConfigDemand,
    ImportFieldConfigConstruction, ImportFieldConfigWorkProgress,
    PrintTemplate, PrintFieldConfig, TemplateFieldMapping)
from models.audit import ChangeHistory
