-- RAG 企业级骨架：单用户先行，预留 user_id / 多租户字段
-- 字符集由 MySQL 启动参数指定为 utf8mb4

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- 文档注册与索引状态（双写 Chroma + ES 的治理真相源）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_registry (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  doc_id VARCHAR(64) NOT NULL COMMENT '业务文档稳定 ID',
  version INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '同一 doc 的版本号，重索引递增',
  filename VARCHAR(512) NULL,
  content_hash VARCHAR(128) NULL COMMENT '整文档或解析结果 hash，幂等用',
  status ENUM(
    'pending',
    'parsing',
    'indexing',
    'indexed',
    'failed',
    'deleted'
  ) NOT NULL DEFAULT 'pending',
  error_message TEXT NULL,
  chunk_count INT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uk_doc_version (doc_id, version),
  KEY idx_status_updated (status, updated_at),
  KEY idx_doc_id (doc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 用户画像（单用户可固定 user_id = default）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profile (
  user_id VARCHAR(64) NOT NULL,
  traits JSON NULL COMMENT '偏好、领域、语言等',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 会话与消息
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id VARCHAR(64) NOT NULL,
  title VARCHAR(512) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversation_message (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  conversation_id BIGINT UNSIGNED NOT NULL,
  role ENUM('user', 'assistant', 'system') NOT NULL,
  content MEDIUMTEXT NOT NULL,
  token_count INT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_conversation_created (conversation_id, created_at),
  CONSTRAINT fk_message_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversation (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversation_summary (
  conversation_id BIGINT UNSIGNED NOT NULL,
  summary MEDIUMTEXT NOT NULL,
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (conversation_id),
  CONSTRAINT fk_summary_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversation (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 持久化记忆（结构化事实 / 偏好，带置信度与生命周期）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_item (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id VARCHAR(64) NOT NULL,
  kind VARCHAR(32) NOT NULL COMMENT 'fact / preference / constraint 等',
  content TEXT NOT NULL,
  confidence DECIMAL(4, 3) NOT NULL DEFAULT 1.000,
  source VARCHAR(32) NOT NULL COMMENT 'user_explicit / inferred / admin',
  valid_from DATETIME(3) NULL,
  valid_until DATETIME(3) NULL,
  superseded_by BIGINT UNSIGNED NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_user_kind_created (user_id, kind, created_at),
  KEY idx_user_valid (user_id, valid_until),
  CONSTRAINT fk_memory_superseded
    FOREIGN KEY (superseded_by) REFERENCES memory_item (id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 查询审计（检索与生成可观测）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS query_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id VARCHAR(64) NULL,
  conversation_id BIGINT UNSIGNED NULL,
  query_text TEXT NOT NULL,
  answer_excerpt MEDIUMTEXT NULL,
  retrieved_chunk_ids JSON NULL,
  latency_chroma_ms INT UNSIGNED NULL,
  latency_es_ms INT UNSIGNED NULL,
  latency_total_ms INT UNSIGNED NULL,
  model_name VARCHAR(128) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_created (created_at),
  KEY idx_user_created (user_id, created_at),
  CONSTRAINT fk_audit_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversation (id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 单用户默认行（可按需修改 traits）
-- ---------------------------------------------------------------------------
INSERT INTO user_profile (user_id, traits)
VALUES ('default', JSON_OBJECT('locale', 'zh-CN'))
ON DUPLICATE KEY UPDATE user_id = user_id;
