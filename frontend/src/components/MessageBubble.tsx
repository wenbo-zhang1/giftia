import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../types'
import './MessageBubble.css'

interface Props {
  message: Message
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const hasImage = !!message.image

  const renderContent = useMemo(() => {
    if (hasImage) {
      return (
        <>
          <img src={message.image} alt="uploaded" className="bubble-image" />
          {message.content && (
            <div className="bubble-text">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </>
      )
    }
    return <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
  }, [message.content, message.image, hasImage])

  return (
    <div className={`bubble-row ${isUser ? 'bubble-row--user' : 'bubble-row--assistant'}`}>
      {!isUser && (
        <div className="bubble-avatar bubble-avatar--assistant">忆</div>
      )}
      <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--assistant'} ${hasImage ? 'bubble--has-image' : ''}`}>
        {renderContent}
      </div>
      {isUser && (
        <div className="bubble-avatar bubble-avatar--user">
          我
        </div>
      )}
    </div>
  )
}
