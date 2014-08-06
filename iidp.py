
"""
A Simple bit of output code, just dump some HTML.
"""

def sellProfit(itm):
    if itm['value']:
        return itm['yieldValue'] - itm['value']

    return itm['yieldValue']
    

def sellString(itm):

    template = "<b><span style='color:{}'>{}</span></b> {}"

    def __perc(itm):
        foo = float(min(itm['value'], itm['yieldValue']))
        bar = float(max(itm['value'], itm['yieldValue']))
        return "<small>({:.1%})</small>".format((bar - foo) / foo) if foo != float(0) else ""

    if not itm['value']:
        return template.format('blue', 'Refine', "")

    if itm['value'] < 0.90 * itm['yieldValue']:
        return template.format('blue', 'Refine', __perc(itm))
    if itm['value'] < itm['yieldValue']:
        return template.format('green', 'Refine', __perc(itm))
    if itm['value'] < 1.10 * itm['yieldValue']:
        return template.format('yellow', 'Sell', __perc(itm))
    else:
        return template.format('red', 'Sell', __perc(itm))
    

__document = """ 
<!DOCTYPE html>
<html>
<body>
<h1>{name}</h1>
<p>{location}</p>
{summary}
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


def buildSummary(can):

    def totalYieldTable():


        hrow = "";
        trow = "";
        prow = "";

        totalYield = sorted(can.attainableYield, key=(lambda itm: itm['typeID']))

        for itm in totalYield:
            hrow += th(itm['name'])
            trow += td("{:,}".format(itm['quantity']))
            prow += td("{:,}".format(itm['value']))

        return ("<table border=1>\n" +
                "<tr><th></th>" + hrow + "</tr>\n" + 
                "<tr><td>Quantity</td>" + trow + "</tr>\n" +
                "<tr><td>Valued at</td>" + prow + "</tr>\n" +
                "</table>\n")
    
    top = ("<p>" +
           "Total Sell Value: {:,} ISK <br>" +
           "Total Reprocess Value: {:,} ISK <br>" +
           "</p>\n").format(totalSellValue(can),
                            totalYieldValue(can))
    
    payout = ("<p><b>" +
              "LBP Payout: {:,} ISK <br>" +
              "</b></p>").format(int(0.90 * totalYieldValue(can)))

    mid = ("<div>" +
           "Total Reprocessing Yield: <br>\n" +
           totalYieldTable() +
           "</div>\n")
    
    return top + payout + mid           


def buildHeaders(can):

    header = (th("Group") +
              th("Item") +
              th("Quantity") +
              th("Unit Mineral Value") +
              th("Unit Sell Value") +
              th("Unit Sell Profit") +
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

        row += td("{:,}".format(itm['yieldValue']))
        row += td("{:,}".format(itm['value']) if itm['value'] else str(None))
        row += td("{:,}".format(-sellProfit(itm)))
        row += td(sellString(itm))
        row += td("{:,}".format(itm['quantity'] * itm['yieldValue']))
        row += td("{:,}".format(itm['quantity'] * itm['value']) if itm['value'] else str(None))

        return "<tr>" + row + "</tr>"
    
    return '\n'.join(map(buildRow, can.contents))


def output(cans, args):

    prefix = args['outputprefix'] if args['outputprefix'] else ''

    for can in cans:
        
        out = None
        if args['uniquefiles'] in ['true', 'yes', 'True', 'Yes', '1']:
            out = open(prefix + "{}.{}.html".format(can.name, can.itemID), 'w')
        else:
            out = open(prefix + "{}.html".format(can.name), 'w')            
        
        # Sort the contents, makes a nicer dump. 
        can.contents = sorted(can.contents, key=sellProfit)

        out.write(__document.format(name = can.name,
                                    location = can.locationName,
                                    summary = buildSummary(can),
                                    headers = buildHeaders(can),
                                    rows = buildRows(can)))        
        out.close()
