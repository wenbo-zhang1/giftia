import { useEffect } from 'react'
import './ModelDialog.css'

interface Props {
  onClose: () => void
}

export default function ModelDialog({ onClose }: Props) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content model-dialog" onClick={(e) => e.stopPropagation()}>
        <h3 className="dialog-title">切换模型</h3>
        <p className="model-dialog-desc">
          编辑 <code>backend/model_config.py</code>，修改 <code>CHAT_MODEL</code> 和 <code>CHAT_BASE_URL</code>，
          系统会自动从 <code>.env</code> 中找到对应的 API key。修改后重启后端即可。
        </p>

        <div className="model-dialog-steps">
          <div className="model-dialog-step">1. 打开 <code>backend/model_config.py</code></div>
          <div className="model-dialog-step">2. 修改 <code>CHAT_MODEL</code> 和 <code>CHAT_BASE_URL</code></div>
          <div className="model-dialog-step">3. 确保 <code>.env</code> 中有对应提供商的 API key</div>
          <div className="model-dialog-step">4. 重启后端服务</div>
        </div>

        <h4 className="model-dialog-subtitle">provider → API key 映射（model_config.py 内置）</h4>
        <pre className="model-dialog-code">deepseek    → Deepseek_API_KEY
openai      → OPENAI_API_KEY
zhipu       → ZhipuAI_API_KEY
qwen        → DASHSCOPE_API_KEY
siliconflow → SILICONFLOW_API_KEY</pre>

        <h4 className="model-dialog-subtitle">常用模型配置示例</h4>
        <details className="model-dialog-preset">
          <summary>DeepSeek（默认）</summary>
          <pre className="model-dialog-code">CHAT_MODEL = "deepseek-v4-flash"
CHAT_BASE_URL = "https://api.deepseek.com/v1"
# 需要 .env 中有: Deepseek_API_KEY=sk-xxx</pre>
        </details>
        <details className="model-dialog-preset">
          <summary>OpenAI</summary>
          <pre className="model-dialog-code">CHAT_MODEL = "gpt-4o"
CHAT_BASE_URL = "https://api.openai.com/v1"
# 需要 .env 中有: OPENAI_API_KEY=sk-xxx</pre>
        </details>
        <details className="model-dialog-preset">
          <summary>智谱AI</summary>
          <pre className="model-dialog-code">CHAT_MODEL = "glm-4-flash"
CHAT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
# 需要 .env 中有: ZhipuAI_API_KEY=xxx</pre>
        </details>
        <details className="model-dialog-preset">
          <summary>通义千问</summary>
          <pre className="model-dialog-code">CHAT_MODEL = "qwen-plus"
CHAT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# 需要 .env 中有: DASHSCOPE_API_KEY=sk-xxx</pre>
        </details>
        <details className="model-dialog-preset">
          <summary>SiliconFlow</summary>
          <pre className="model-dialog-code">CHAT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
CHAT_BASE_URL = "https://api.siliconflow.cn/v1"
# 需要 .env 中有: SILICONFLOW_API_KEY=sk-xxx</pre>
        </details>

        <h4 className="model-dialog-subtitle">关于图片上传</h4>
        <p className="model-dialog-note">
          本系统支持图片上传，但需要模型本身具备多模态（识图）能力，
          如 <code>gpt-5.5</code>、<code>glm-5v-Turbo</code>、<code>qwen-3.6-plus</code>、<code>claude-4.6-sonnet</code> 等。
          系统通过模型名称关键词来判断是否多模态，判断逻辑较简陋。
          如果您使用的模型支持多模态但无法上传图片，
          请在 <code>backend/file_processor.py</code> 的 <code>is_multimodal_model()</code> 函数中添加您的模型名称。
        </p>

        <button className="dialog-btn dialog-btn--primary" onClick={onClose}>
          关闭
        </button>
      </div>
    </div>
  )
}