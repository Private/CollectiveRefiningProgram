
"""
A Simple bit of output code, just dump some HTML.
"""

import json


def sellProfit(itm):
    if itm['value']:
        return itm['yieldValue'] - itm['value']

    return itm['yieldValue']
    

def sellString(itm):

    template = "<b><span style='color:{}'>{}</span></b>"

    if not itm['value']:
        return template.format('blue', 'Refine')

    if itm['value'] < 0.90 * itm['yieldValue']:
        return template.format('blue', 'Refine')
    if itm['value'] < itm['yieldValue']:
        return template.format('green', 'Refine')
    if itm['value'] < 1.10 * itm['yieldValue']:
        return template.format('yellow', 'Sell')
    else:
        return template.format('red', 'Sell')
    

__document = """ 
<!DOCTYPE html>
<html>
<body>
<h1>{name}</h1>
<p>{location}</p>
{summary}
{groups}
<div>
<h3>Item Breakdown</h3>
<table border=1>
{headers}
{rows}
</table>
</div>
</body>
</html>
"""

def wrap(s, tag):
    return '<' + tag + '>' + str(s) + '</' + tag + '>'

def td(s):
    return wrap(s, 'td')

def th(s):
    return wrap(s, 'th')


def totalSellValue(container):
    return sum(map(lambda itm: itm['value'] * itm['quantity'] 
                   if itm['value'] else 0.0, container.contents))


def totalYieldValue(container):
    return sum(map(lambda itm: itm['value'] * itm['quantity']
                   if itm['value'] else 0.0, container.attainableYield))


def buildSummary(can, grouppayouts):

    def totalYieldTable():


        hrow = "";
        trow = "";
        prow = "";

        totalYield = sorted(can.attainableYield, key=(lambda itm: itm['typeID']))

        for itm in totalYield:
            hrow += th(itm['name'])
            trow += td("{:,.2f}".format(itm['quantity']))
            prow += td("{:,.2f}".format(itm['value']))

        return ("<table border=1>\n" +
                "<tr><th></th>" + hrow + "</tr>\n" + 
                "<tr><td>Quantity</td>" + trow + "</tr>\n" +
                "<tr><td>Valued at</td>" + prow + "</tr>\n" +
                "</table>\n")
    
    top = ("<p>" +
           "Total Sell Value: {:,.2f} ISK <br>" +
           "Total Reprocess Value: {:,.2f} ISK <br>" +
           "</p>\n").format(totalSellValue(can),
                            totalYieldValue(can))

    groups = ''.join(map(lambda group: "{group}: {:,.2f} ISK <br>".format(grouppayouts[group], group = group) 
                         if grouppayouts[group] > 0 
                         else '', 
                         grouppayouts))

    breakdown = ("<p>" +
                 "<h4>LBP Payouts by group:</h4>" + 
                 "Refining Yield: {:,.2f} ISK <br>" +
                 "{groups}"
                 "</p>\n").format(0.95 * totalYieldValue(can), groups = groups)
    
    payout = ("<p><b>" +
              "Total LBP Payout: {:,.2f} ISK <br>" +
              "</b></p>").format(int(0.95 * totalYieldValue(can) +
                                     sum([grouppayouts[group] for group in grouppayouts])))

    mid = ("<div>" +
           "Total Reprocessing Yield: <br>\n" +
           totalYieldTable() +
           "</div>\n")
    
    return top + breakdown + payout + mid           


def buildGroups(grouprates, groupitems):

    # Do we actually have any groups to output?
    if all([groupitems[group] == [] for group in groupitems]):
        return ''

    def buildGroup(group):

        # No items, no output. 
        if not groupitems[group]: return ''

        __format = "<div><h3>{group}</h3><div>{summary}</div><div>{table}</div>"
        __table = "<table border=1>{headers}{rows}</table>"

        # Item - Quantity - Unit Sell Value - Total Sell Value
        __headers = ("<tr>" +
                     th("Item") +
                     th("Quantity") +
                     th("Unit Sell Value") +
                     th("Total Sell Value") +
                     "</tr>")
        
        total = sum(map(lambda itm: itm['quantity'] * itm['value'], groupitems[group]))

        summary = ('<p>Total Value: {:,.2f} ISK</p>' +
                   '<p>LBP Payout: {:,.2f} ISK</p')
        summary = summary.format(total, float(grouprates[group]) * total)
        
        __row = "<tr><td>{}</td><td>{}</td><td>{:,.2f}</td><td>{:,.2f}</td></tr>"
        __rows = '\n'.join(map(lambda itm: __row.format(itm['name'],
                                                        itm['quantity'],
                                                        itm['value'],
                                                        itm['quantity'] * itm['value']), 
                               sorted(groupitems[group],
                                      key = lambda itm: -itm['quantity'] * itm['value'])))
        
        return __format.format(group = group,
                               summary = summary,
                               table = __table.format(headers = __headers,
                                                      rows = __rows))

    __format = '<div>{groups}</div>'

    return __format.format(groups = ''.join(map(buildGroup, groupitems)))


def buildHeaders(can):

    header = (th("Group") +
              th("Item") +
              th("Quantity") +
              th("Unit Mineral Value") +
              th("Unit Sell Value") +
              th("<b>Unit Sell Profit</b>") +
              th("Liquidate") +
              th("Total Mineral Value") +
              th("Total Sell Value")) 

    return "<tr>" + header + "</tr>"


def buildRows(can):

    def buildRow(itm):

        row = "<td>{group}</td><td>{name}</td><td>{quantity}</td>"

        row = row.format(group = itm['groupName'],
                         name = itm['name'],
                         quantity = itm['quantity'])

        row += td("{:,.2f}".format(itm['yieldValue']))
        row += td("{:,.2f}".format(itm['value']) if itm['value'] else str(None))
        row += td("<b>{:,.2f}</b>".format(-sellProfit(itm)))
        row += td(sellString(itm))
        row += td("{:,.2f}".format(itm['quantity'] * itm['yieldValue']))
        row += td("{:,.2f}".format(itm['quantity'] * itm['value']) if itm['value'] else str(None))

        return "<tr>" + row + "</tr>"
    
    return '\n'.join(map(buildRow, can.contents))


def output(cans, args):

    prefix = args['outputprefix'] if args['outputprefix'] else ''

    # The JSON roundabout is - well - I prefer not to use eval. This seems like a better hack.
    grouprates = json.loads(args['marketgroups'].replace("'", "\""))
    groupitems = {}    

    for can in cans:
        
        location = '[' + can.locationName.split()[0] + ']' 
        
        out = None
        if args['uniquefiles'] in ['true', 'yes', 'True', 'Yes', '1']:
            out = open(prefix + "{}.{}.{}.html".format(location, can.name, can.itemID), 'w')
        else:
            out = open(prefix + "{}.{}.html".format(location, can.name), 'w')            

        # We need to collect the items for the special marketgroups. 
        groupitems = { group: 
                       [itm for itm in can.contents if itm['groupName'] == group] 
                       for group in grouprates.keys() }

        grouppayouts  = { group:
                          float(grouprates[group]) * 
                          sum(map(lambda itm:  
                                  itm['quantity'] * itm['value'], groupitems[group]))
                          for group in grouprates.keys() }        
        
        # Sort the contents, makes a nicer dump. 
        can.contents = sorted(can.contents, key=sellProfit)

        out.write(__document.format(name = can.name,
                                    location = can.locationName,
                                    summary = buildSummary(can, grouppayouts),
                                    groups = buildGroups(grouprates, groupitems),
                                    headers = buildHeaders(can),
                                    rows = buildRows(can)))        
        out.close()
