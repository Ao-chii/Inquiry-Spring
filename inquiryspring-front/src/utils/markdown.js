import marked from 'marked';

export function markdownToHtml(markdown) {
    return marked.parse(markdown);
}
