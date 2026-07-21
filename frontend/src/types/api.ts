export interface ApiErrorBody {
  error: { code: string; message: string; request_id: string; details: unknown }
}

export interface User {
  id: string
  email: string
  display_name: string
  avatar_url: string | null
  theme: 'light' | 'dark' | 'system'
  memory_enabled: boolean
  default_assistant_id: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  access_expires_at: string
  user: User
}

export interface UsageSummary {
  conversations: number
  tasks: number
  documents: number
  input_tokens: number
  output_tokens: number
}

export interface ModelConfig {
  id: string
  credential_id: string | null
  provider: string
  model_id: string
  alias: string
  parameters: Record<string, unknown>
  is_default: boolean
}

export interface Credential {
  id: string
  provider: string
  display_name: string
  base_url: string
  key_hint: string
  is_active: boolean
}

export interface ProviderInfo {
  id: string
  name: string
  base_url: string
  example_models: string[]
}

export interface Assistant {
  id: string
  owner_id: string | null
  name: string
  slug: string
  description: string
  avatar: string
  system_prompt: string
  opening_message: string
  category: string
  visibility: string
  model_config: AssistantModelSettings
  usage_count: number
  is_featured: boolean
  installed: boolean
  knowledge_file_ids: string[]
}

export interface AssistantModelSettings {
  model_config_id: string | null
  temperature: number
  max_tokens: number | null
}

export interface Conversation {
  id: string
  assistant_id: string | null
  model_config_id: string | null
  title: string
  archived_at: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  conversation_id: string
  parent_id: string | null
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  status: 'pending' | 'streaming' | 'completed' | 'stopped' | 'failed'
  model: string | null
  input_tokens: number
  output_tokens: number
  error_code: string | null
  created_at: string
  updated_at: string
  attachments: MessageAttachment[]
  tool_status?: string
}

export interface MessageAttachment {
  id: string
  file_id: string
  attachment_type: string
  attachment_metadata: Record<string, unknown>
}

export interface FileAsset {
  id: string
  original_name: string
  mime_type: string
  size: number
  sha256: string
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}

export interface ToolItem {
  id: string
  name: string
  slug: string
  description: string
  icon: string
  category: string
  access_type: 'external_link' | 'openai_tool' | 'provider_api'
  external_url: string | null
  rating: number
  is_active: boolean
  is_favorite: boolean
}

export interface TaskItem {
  id: string
  template_id: string | null
  title: string
  content: string
  status: 'todo' | 'doing' | 'done'
  priority: 'low' | 'normal' | 'high'
  due_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskTemplate {
  id: string
  title: string
  description: string
  icon: string
  prompt_template: string
  category: string
}

export interface DocumentItem {
  id: string
  title: string
  content_json: Record<string, unknown>
  content_text: string
  current_version: number
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface DocumentVersion {
  id: string
  document_id: string
  version: number
  snapshot: Record<string, unknown>
  created_at: string
}

export interface MemoryItem {
  id: string
  source_message_id: string | null
  content: string
  category: string
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface ResourceItem {
  id: string
  owner_id: string | null
  resource_type: string
  title: string
  description: string
  content: string
  visibility: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface SearchResult {
  id: string
  result_type: 'conversation' | 'task' | 'document' | 'resource'
  title: string
  snippet: string
  path: string
}
