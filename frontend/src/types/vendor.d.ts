declare module 'markdown-it' {
  export interface MarkdownItOptions {
    html?: boolean
    linkify?: boolean
    breaks?: boolean
    highlight?: (source: string, language: string) => string
  }

  export default class MarkdownIt {
    constructor(options?: MarkdownItOptions)
    render(source: string): string
  }
}
