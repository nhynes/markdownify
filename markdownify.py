#!/bin/python

#requirements:
#   lxml
#   cssselect

from lxml import etree, html
import argparse
import re
import string

#contants
NEWLINE = '\n'

#regexes
heading_tag = re.compile('h([1-6])')
whitespace = re.compile('\s+')
sentence = re.compile('([^.?!]{2,}\.|\?\!)\s+') #matches the end of a sentence
fakelist = re.compile('\s+([0-9]+)\. ')
fakeem = re.compile('(\*|_)+')

#some classes of elements
void_elems = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen', 'link', 'meta', 'param', 'source', 'track', 'wbr']
inline_nonmarkdown_elem = ['big', 'small', 'abbr', 'acronym', 'cite', 'dfn', 'kbd', 'samp', 'var', 'bdo', 'map', 'object', 'q', 'script', 'span', 'sub', 'sup', 'button', 'input', 'label', 'select']

def repeat_string(string, times):
    """
    Returns a string repeated a number of times

    Arguments:
        string - the string to repeat
        times  - the number of times to repeat the string
    """
    if times <= 0:
        return ''
    return ''.join([string for i in range(times)])

def indent(level, spaces=4):
    """
    Returns an indentation string

    Arguments:
        level  - the indentation level
        spaces - how many spaces per level. Default 4
    """
    return ''
    return repeat_string('  ', level)

def quote(level):
    return repeat_string('> ', level)

def prettify(text, indent_level=0, quote_level=0):
    """
    Returns the input text in a format better suited for Markdown

    Arguments:
        text         - the text to prettify
        indent_level - the indent level for line-broken sentences
        quote_level  - the quotation level (also for line-broken sentences)
    """
    if text == None or len(text.strip()) == 0:
        return ''

    text = text.strip(NEWLINE)
    text = whitespace.sub(' ', text)
    text = sentence.sub(r'\1\n' + indent(indent_level) + quote(quote_level), text) #slow
    text = fakelist.sub(r'\1\\\. ', text)
    text.replace('*', '\\*') #ugly
    text.replace('_', '\\_') #inelegant
    # text = fakeem.sub(repeat_string('\\' + r'\1'[0],len(r'\1')), text)
    return text

def require_newlines(string, number, exact=False):
    """
    Ensures that the string has at least a certain number of trailing newlines

    Arguments:
        string - the string to check
        number - the number of newlines required. Must be >= 0
        exact  - True if there should be exactly number newlines
    """
    found_newlines = 0
    for i in range(len(string))[::-1]:
        if string[i] != NEWLINE:
            break
        else:
            found_newlines += 1

    if found_newlines == 0 or exact:
        return string.rstrip(NEWLINE) + repeat_string(NEWLINE, number)
    else:
        new_newlines = max(number - found_newlines, 0)
        if new_newlines == 0:
            return string
        else:
            required_newlines = repeat_string(NEWLINE, new_newlines)
            return string + required_newlines

def make_tag(elem, tagtype):
    """
    Returns the element as an HTML tag string.

    Arguments:
        elem - the element to tagify
        tagtype - "start" or "end"
    """
    if tagtype == 'start':
        attribs = ' '.join([name + '="' + value + '"' for (name, value) in elem.items()])
        if len(attribs) > 0:
            attribs = ' ' + attribs
        return '<' + elem.tag + attribs + '>'
    elif tagtype == 'end':
        if elem.tag in void_elems:
            return ''
        else:
            return '</' + elem.tag + '>'

def make_list_env(markdown, elem, text):
    markdown = require_newlines(markdown, 1)
    markdown += text.lstrip()
    markdown = require_newlines(markdown, 1)
    return markdown

argparser = argparse.ArgumentParser(description='Convert HTML to Markdown')
argparser.add_argument('file', metavar='file', type=str, help='the HTML file to convert')
argparser.add_argument('-s', '--selector', metavar='selector', default='body', help='only convert the contents of elements matched by the CSS3 selector')
argparser.add_argument('-l', '--move-links', action='store_true', help='move URLs to bottom of file')
args = argparser.parse_args()

page = html.parse(args.file)
html = page.getroot().cssselect(args.selector)

move_links = args.move_links
links = {}

for element in html:
    markdown = ""
    events = etree.iterwalk(element, events=('start', 'end'))

    indent_level = 0

    quote_level = 0

    list_item_number = []
    list_type = []

    verbatim_start = None

    for event, elem in events:
        if elem in html:
            continue

        tag = elem.tag
        text = prettify(elem.text, indent_level, quote_level)
        tail = prettify(elem.tail, indent_level, quote_level)

        if event == 'start':
            if verbatim_start != None:
                markdown += make_tag(elem, event) + text
                continue

            if tag == 'a':
                url = elem.get('href')
                if url != None:
                    markdown += '[' + text + ']'
                    if move_links:
                        links[text] = url
                        markdown += '[]'
                    else:
                        markdown += '(' + url + ')'
                elif heading_tag.match(elem.getparent().tag) != None:
                    markdown += text
                    markdown = require_newlines(markdown, 1)
                else:
                    markdown += text
            elif tag == 'b' or tag == 'strong':
                markdown += '**' + text
            elif tag == 'blockquote':
                if elem.getparent().tag == 'li' or (len(elem) == 1 and elem[0].tag == 'code'):
                    #this is getting triggered for some reason
                    indent_level += 1
                quote_level += 1
                markdown = require_newlines(markdown, 1)
            elif tag == 'br':
                # markdown = require_newlines(markdown.rstrip(), 0, True)
                markdown = markdown.rstrip() + '  \n'
            elif tag == 'code' or tag == 'tt':
                parent = elem.getparent()
                if (parent.tag == 'blockquote' or parent.tag == 'pre') and len(parent) == 1:
                    markdown = require_newlines(markdown, 1)
                    markdown += text #todo: this
                    markdown = require_newlines(markdown, 1)
                elif '`' in text:
                    markdown += '``'
                else:
                  markdown += '`'  + text
            elif heading_tag.match(tag) != None:
                heading_level = int(heading_tag.match(tag).group(1))
                hashes = repeat_string('#', heading_level)
                markdown = require_newlines(markdown, 2, True)
                markdown +=  indent(indent_level) + quote(quote_level) + hashes + ' ' + text.replace(r'\s', ' ')
            elif tag == 'hr':
                markdown = require_newlines(markdown, 1)
                markdown += '----------\n'
            elif tag == 'i' or tag == 'em':
                markdown += '*' + text
            elif tag == 'li':
                if len(list_type) == 0: #if lonely li (not inside a list)
                    list_type.append('ul')
                    markdown = make_list_env(markdown, elem, '')

                type = list_type[-1]
                if type == 'ol':
                    item_number = list_item_number[-1]
                    list_item_number[-1] += 1
                    markdown += indent(indent_level) + quote(quote_level) + str(item_number) + '. ' + text
                elif type == 'ul':
                    markdown += indent(indent_level) + quote(quote_level) + '+ ' + text
            elif tag == 'ol':
                list_type.append('ol')
                list_item_number.append(1)
                markdown = make_list_env(markdown, elem, text)
            elif tag == 'p':
                newlines = 2
                parent = elem.getparent()
                if elem == elem.getparent()[0] and (parent.tag == 'ul' or parent.tag == 'ol'):
                    #if first child of a list
                    newlines = 0
                markdown = require_newlines(markdown, newlines, True)
                markdown += indent(indent_level) + quote(quote_level) + text.lstrip()
            elif tag == 'pre':
                markdown = require_newlines(2)
                indent_level += 1
                markdown += text
            elif tag == 'ul':
                list_type.append('ul')
                markdown = make_list_env(markdown, elem, text)
            else:
                if tag not in inline_nonmarkdown_elem:
                    verbatim_start = elem        
                markdown += make_tag(elem, event) + text


        elif event == 'end':
            if verbatim_start != None:
                markdown += make_tag(elem, event) + '\n' + tail
                if verbatim_start == elem:
                    verbatim_start = None
                continue

            if tag == 'a':
                markdown += tail
            elif tag == 'b' or tag == 'strong':
                markdown += '**' + tail
            elif tag == 'blockquote':
                if elem.getparent().tag == 'li':
                    indent_level -= 1
                quote_level -= 1
                markdown = require_newlines(markdown, 1)
            elif tag == 'br':
                markdown += tail.lstrip()
            elif tag == 'code' or tag == 'tt':
                parent = elem.getparent()
                if (parent.tag == 'blockquote' or parent.tag == 'pre') and len(parent) == 1:
                    markdown = require_newlines(markdown, 2)
                    markdown += tail
                elif '`' in text:
                    markdown += '``' + tail
                else:
                  markdown += '`'  + tail
            elif heading_tag.match(tag) != None:
                markdown = require_newlines(markdown, 2, True)
                markdown += tail
            elif tag == 'hr':
                markdown += tail.lstrip()
            elif tag == 'i' or tag == 'em':
                markdown += '*' + tail
            elif tag == 'li':
                markdown = require_newlines(markdown, 1)
                markdown += tail.lstrip()
            elif tag == 'ol':
                list_type.pop()
                list_item_number.pop()
                markdown = require_newlines(markdown, 1)
                markdown += tail.lstrip()
            elif tag == 'p':
                markdown = require_newlines(markdown, 2, True)
                markdown += tail.lstrip()
            elif tag == 'ul':
                list_type.pop()
                markdown = require_newlines(markdown, 1)
                markdown += tail.lstrip()
            else:
                markdown += make_tag(elem, event) + tail
    
    #add links to bottom of page
    if len(links) > 0:
        markdown += '\n\n'
        for link in links:
            markdown += '[' + link + ']: ' + links[link] + NEWLINE

    print(markdown.strip())