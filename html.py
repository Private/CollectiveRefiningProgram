
"""
  A Simple bit of output code, just dump some HTML.
"""

def sellProfit(itm):
    if itm['value']:
        return itm['yieldvalue'] - itm['value']

    return itm['yieldvalue']
    

def sellString(itm):

    template = "<b><span style='color:{}'>{}</span></b> {}"

    def __perc(itm):
        foo = float(min(itm['value'], itm['yieldvalue']))
        bar = float(max(itm['value'], itm['yieldvalue']))
        return "<small>({:.1%})</small>".format((bar - foo) / foo) if foo != float(0) else ""

    if not itm['value']:
        return template.format('blue', 'Refine', "")

    if itm['value'] < 0.90 * itm['yieldvalue']:
        return template.format('blue', 'Refine', __perc(itm))
    if itm['value'] < itm['yieldvalue']:
        return template.format('green', 'Refine', __perc(itm))
    if itm['value'] < 1.10 * itm['yieldvalue']:
        return template.format('yellow', 'Sell', __perc(itm))
    else:
        return template.format('red', 'Sell', __perc(itm))
    

__document = """ 
<!DOCTYPE html>
<html>
<body>
<h1>{name}</h1>
<p>{location}</p>
<div>
Current Time: {time} <br>
Cached Until: {cache} <br>
</div>
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


def buildSummary(can):

    def totalYieldTable():
        total, names = can.totalYield()

        hrow = "";
        trow = "";
        prow = "";

        for (typeID, n) in sorted(total.items(), key=(lambda (typeID, _): int(typeID))):
            hrow += th(names[typeID])
            trow += td("{:,}".format(n))
            prow += td("{:,}".format(can.yieldprices[typeID]))

        return ("<table border=1>\n" +
                "<tr><th></th>" + hrow + "</tr>\n" + 
                "<tr><td>Quantity</td>" + trow + "</tr>\n" +
                "<tr><td>Valued at</td>" + prow + "</tr>\n" +
                "</table>\n")
    
    top = ("<p>" +
           "Total Sell Value: {:,} ISK <br>" +
           "Total Reprocess Value: {:,} ISK <br>" +
           "Total Maximum Value: {:,} ISK <br>" +
           "</p>\n").format(can.totalSellValue(),
                            can.totalYieldValue(),
                            can.totalMaximumValue())
    
    payout = ("<p><b>" +
              "LBP Payout: {:,} ISK <br>" +
              "</b></p>").format(int(0.90 * can.totalYieldValue()))

    mid = ("<div>" +
           "Total Reprocessing Yield: <br>\n" +
           totalYieldTable() +
           "</div>\n")
    
    return top + payout + mid           

def buildOptimize(can):

    header = ("<tr>" + 
              th("Group") +
              th("Item") +
              th("Quantity") +
              th("Unit Mineral Value") +
              th("Unit Sell Value") +
              th("Unit Profit") +
              th("Total Profit") +
              "</tr>")
    
    def buildRow(itm):
        return ("<tr>" +
                td(itm['groupName']) +
                td(itm['name']) +
                td(itm['quantity']) +
                td("{:,}".format(itm['yieldvalue'])) +
                td("{:,}".format(itm['value'])) +
                td("{:,}".format(sellProfit(itm))) +
                td("{:,}".format(itm['quantity'] * 
                                 (itm['value'] - itm['yieldvalue']))) +
                "</tr>")

    rows = map(buildRow,
               sorted(can.contents, 
                      key=(lambda itm: itm['yieldvalue'] - itm['value']))[0:20])
    
    return header + ''.join(rows)

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

        row += td("{:,}".format(itm['yieldvalue']))
        row += td("{:,}".format(itm['value']) if itm['value'] else str(None))
        row += td("{:,}".format(-sellProfit(itm)))
        row += td(sellString(itm))
        row += td("{:,}".format(itm['quantity'] * itm['yieldvalue']))
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
                                    location = can.location,
                                    time = can.currentTime,
                                    cache = can.cachedUntil,
                                    summary = buildSummary(can),
                                    headers = buildHeaders(can),
                                    rows = buildRows(can)))        
        out.close()
