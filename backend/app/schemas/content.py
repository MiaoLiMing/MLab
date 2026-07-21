from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from app.schemas.common import ORMModel


class AssistantModelConfig(BaseModel):
    model_config_id: UUID | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=100_000)


class AssistantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    avatar: str = Field(default="AI", max_length=32)
    system_prompt: str = Field(default="", max_length=20_000)
    opening_message: str = Field(default="", max_length=2_000)
    category: str = Field(default="general", max_length=50)
    assistant_config: AssistantModelConfig = Field(
        default_factory=AssistantModelConfig,
        validation_alias=AliasChoices("assistant_config", "model_config"),
        serialization_alias="model_config",
    )
    knowledge_file_ids: list[UUID] = Field(default_factory=list, max_length=20)


class AssistantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    avatar: str | None = Field(default=None, max_length=32)
    system_prompt: str | None = Field(default=None, max_length=20_000)
    opening_message: str | None = Field(default=None, max_length=2_000)
    category: str | None = Field(default=None, max_length=50)
    assistant_config: AssistantModelConfig | None = Field(
        default=None,
        validation_alias=AliasChoices("assistant_config", "model_config"),
        serialization_alias="model_config",
    )
    knowledge_file_ids: list[UUID] | None = Field(default=None, max_length=20)


class AssistantResponse(ORMModel):
    id: UUID
    owner_id: UUID | None
    name: str
    slug: str
    description: str
    avatar: str
    system_prompt: str
    opening_message: str
    category: str
    visibility: str
    assistant_config: AssistantModelConfig = Field(
        validation_alias=AliasChoices("assistant_config", "model_config"),
        serialization_alias="model_config",
    )
    usage_count: int
    is_featured: bool
    installed: bool = False
    knowledge_file_ids: list[UUID] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)
    assistant_id: UUID | None = None
    model_config_id: UUID | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    archived: bool | None = None


class MessageAttachmentResponse(ORMModel):
    id: UUID
    file_id: UUID
    attachment_type: str
    attachment_metadata: dict[str, Any]


class MessageResponse(ORMModel):
    id: UUID
    conversation_id: UUID
    parent_id: UUID | None
    role: str
    content: str
    status: str
    model: str | None
    input_tokens: int
    output_tokens: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    attachments: list[MessageAttachmentResponse] = Field(default_factory=list)


class ConversationResponse(ORMModel):
    id: UUID
    assistant_id: UUID | None
    model_config_id: UUID | None
    title: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    model_config_id: UUID | None = None
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=10)
    source_message_id: UUID | None = None


class ToolResponse(ORMModel):
    id: UUID
    name: str
    slug: str
    description: str
    icon: str
    category: str
    access_type: str
    external_url: str | None
    rating: float
    is_active: bool
    is_favorite: bool = False


class ToolExecuteRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    message_id: UUID | None = None


class ToolExecuteResponse(BaseModel):
    execution_id: UUID
    output: dict[str, Any]


class TaskTemplateResponse(ORMModel):
    id: UUID
    title: str
    description: str
    icon: str
    prompt_template: str
    category: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=20_000)
    template_id: UUID | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=20_000)
    status: str | None = Field(default=None, pattern="^(todo|doing|done)$")
    priority: str | None = Field(default=None, pattern="^(low|normal|high)$")
    due_at: datetime | None = None


class TaskResponse(ORMModel):
    id: UUID
    template_id: UUID | None
    title: str
    content: str
    status: str
    priority: str
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskAIRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=1000)
    model_config_id: UUID | None = None


class AITextResponse(BaseModel):
    content: str


class DocumentCreate(BaseModel):
    title: str = Field(default="无标题文稿", max_length=200)
    content_json: dict[str, Any] = Field(default_factory=dict)
    content_text: str = ""


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_json: dict[str, Any] | None = None
    content_text: str | None = None
    create_version: bool = False


class DocumentResponse(ORMModel):
    id: UUID
    title: str
    content_json: dict[str, Any]
    content_text: str
    current_version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class DocumentVersionResponse(ORMModel):
    id: UUID
    document_id: UUID
    version: int
    snapshot: dict[str, Any]
    created_at: datetime


class AIActionRequest(BaseModel):
    action: str = Field(pattern="^(rewrite|continue|summarize)$")
    instruction: str | None = Field(default=None, max_length=1000)
    selected_text: str | None = Field(default=None, max_length=50_000)


class ResourceCreate(BaseModel):
    resource_type: str = Field(max_length=30)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    content: str = ""
    tags: list[str] = Field(default_factory=list, max_length=20)


class ResourceResponse(ORMModel):
    id: UUID
    owner_id: UUID | None
    resource_type: str
    title: str
    description: str
    content: str
    visibility: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class FileResponse(ORMModel):
    id: UUID
    original_name: str
    mime_type: str
    size: int
    sha256: str
    created_at: datetime


class SearchResult(BaseModel):
    id: UUID
    result_type: str
    title: str
    snippet: str
    path: str


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    category: str = Field(default="preference", max_length=30)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    category: str | None = Field(default=None, max_length=30)
    enabled: bool | None = None


class MemoryResponse(ORMModel):
    id: UUID
    source_message_id: UUID | None
    content: str
    category: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
