import sys
import os
import shutil
import logging
from collections import defaultdict


logger = logging.getLogger()


HTML_TEMPLATE = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 2.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">\n<head>\n\t<meta http-equiv="content-type" content="text/html; charset=utf-8" />\n\n\t<!-- jQuery -->\n\t<script type="text/javascript" src="./static/jquery-1.11.3.min.js"></script>\n\n\t<!-- Tipped -->\n\t<script type="text/javascript" src="./static/tipped.js"></script>\n\t<link rel="stylesheet" type="text/css" href="./static/tipped.css" />\n\t<script type=\'text/javascript\'>\n\t$(document).ready(function() {\n\t  Tipped.create(\'.boxes .box\');\n\t  });\n\t  </script>\n\n\t<!-- Style -->\n\t<link rel="stylesheet" type="text/css" href="./static/style.css" />\n\t<link rel="stylesheet" type="text/css" href="./static/edl.css" />\n\t<meta name="robots" content="noindex,nofollow" />\n\n\t<!-- Tooltip -->\n\t<script type="text/javascript">\n\t  $(document).ready(function() {\n\t      Tipped.create(\'.inline\');\n\t        });\n\t</script>\n\n\t<!-- Highlight -->\n\t<script type="text/javascript" src="./static/highlight.js"></script>\n\n\t<!-- Button show hide -->\n\t<script type="text/javascript">\n\t  function toggle_visibility(id) {\n\t  var e = document.getElementById(id);\n\t  if(e.style.display == \'block\')\n          e.style.display = \'none\';\n\t  else\n          e.style.display = \'block\';\n\t  }\n\t</script>\n\n\t<!-- Button show and hide all-->\n\t<script type="text/javascript">\n\t  var divState = {};\n\t  function showhide(id) {\n\t  if (document.getElementById) {\n          var divid = document.getElementById(id);\n          divState[id] = (divState[id]) ? false : true;\n          //close others\n          for (var div in divState){\n            if (divState[div] && div != id){\n                document.getElementById(div).style.display = \'none\';\n                divState[div] = false;\n          }\n          }\n        divid.style.display = (divid.style.display == \'block\' ? \'none\' : \'block\');\n\t  }\n\t  }\n\t</script>\n</head>\n%s</body>\n</html>\n'
KBID_TEMPLATE = '<a href="%s%s" target="_blank">%s</a>'
TOOLTIP_SPAN_TEMPLATE = '<span id=\'%s\' class=\'inline\' data-tipped-options="inline: \'d%s\'">%s</span>'
TOOLTIP_DIV_TEMPLATE = '<div id=\'d%s\' style=\'display:none\'>%s</div>'

KBID_PREFIX = {
    'Tencent_KG': 'http://10.93.128.136:8081/get_entry?kbid=',
    'Wikipedia': 'https://en.wikipedia.org/wiki/',
    'DBpedia': 'http://dbpedia.org/page/',
    'Wikidata': 'https://www.wikidata.org/wiki/'
}


def get_html(em):
    if em.entity:
        mention_span = '<span id="linkable">%s</span>' % (em.text)
    else:
        mention_span = '<span id="nil">%s</span>' % (em.text)
    mid = 'm_%s_%s' % (em.beg, em.end)
    tooltip_span = TOOLTIP_SPAN_TEMPLATE % (mid, mid, mention_span)
    tooltip_info = []

    tooltip_info.append('mention: %s' % em.text)
    tooltip_info.append('mention type: %s' % em.etype)

    tooltip_info.append('')
    if em.entity:
        if em.entity._kbids:
            for i in em.entity._kbids:
                line = '%s: ' % i
                line += KBID_TEMPLATE % (KBID_PREFIX[i],
                                         em.entity._kbids[i],
                                         em.entity._kbids[i])
                tooltip_info.append(line)
        else:
            line = 'Tencent_KG: '
            line += KBID_TEMPLATE % (KBID_PREFIX['Tencent_KG'],
                                     em.entity.kbid, em.entity.kbid)
            tooltip_info.append(line)
    else:
        tooltip_info.append('kbid: NIL')

    tooltip_info.append('')
    if em.entity:
        if em.entity.etypes:
            tooltip_info.append('Types:')
            tooltip_info += em.entity.etypes
            tooltip_info.append('')
        if em.entity.misc:
            if 'instance_of' in em.entity.misc:
                r = []
                for qid, label in em.entity.misc['instance_of']:
                    r.append(KBID_TEMPLATE % \
                             (KBID_PREFIX['Wikidata'], qid, label))
                tooltip_info.append('instance of: %s' % '; '.join(r))
            if 'subclass_of' in em.entity.misc:
                r = []
                for qid, label in em.entity.misc['subclass_of']:
                    r.append(KBID_TEMPLATE % \
                             (KBID_PREFIX['Wikidata'], qid, label))
                tooltip_info.append('subclass of: %s' % '; '.join(r))
            if 'descriptions.en' in em.entity.misc:
                tooltip_info.append('Description:')
                tooltip_info.append(em.entity.misc['descriptions.en'])

    tooltip_div = TOOLTIP_DIV_TEMPLATE % (mid, '<br>'.join(tooltip_info))
    return tooltip_span + tooltip_div


def pretty(text):
    text = text.replace('\n', '<br>')
    return text


def strip(text):
    text = text.replace('\t', '') \
               .replace('\n', '') \
               .replace('\r', '') \
               .replace('\u3000', '')
    return text


def visualize(text, entitymentions, outpath=None, stats=False):
    stats_html = ''
    if stats:
        stats_list = []
        count = defaultdict(int)
        for em in entitymentions:
            if em.entity:
                kbid = em.entity.kbid
            else:
                continue
            count[(kbid, em.text)] += 1
        for i in sorted(count.items(), key=lambda x: x[1], reverse=True):
            stats_list.append('%s %s %s' % (i[0][0], i[0][1], i[1]))
        stats_html = '<hr>' + '<br>\n'.join(stats_list) + '<br><hr>\n'

    text_list = list(text.replace('<', '{').replace('>', '}'))
    for em in entitymentions:
        try:
            if strip(text[em.beg:em.end]) != em.text:
                em.end += 1
            assert strip(text[em.beg:em.end]) == em.text
        except AssertionError:
            msg = 'Unmatched mention: expected \'%s\' %s %s, got %s' % \
                (em.text, em.beg, em.end, repr(text[em.beg:em.end]))
            logger.warning(msg)
            continue
        text_list[em.beg] = get_html(em)
        for n in range(em.beg+1, em.end):
            text_list[n] = ''

    if not outpath:
        text_html = stats_html + pretty(''.join(text_list))
        return text_html
    else:
        text_html = HTML_TEMPLATE % stats_html + pretty(''.join(text_list))
        with open(outpath, 'w') as fw:
            fw.write(text_html)


def copy_config_files(outdir):
    pwd = os.path.dirname(os.path.abspath(__file__))
    try:
        shutil.copytree('%s/static' % pwd, '%s/static' % outdir)
    except FileExistsError:
        pass
