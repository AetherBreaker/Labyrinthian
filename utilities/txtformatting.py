from textwrap import shorten
from string import Template
from math import floor

class mkTable():
    def fromListofDicts(dataIn: list, columns: list, columnsmaxwidth: dict, maxwidth: int, templstr: str='', wrapstr: str='', itemwrap: dict = None):
        """
        Attributes
        ----------
        dataIn: :class:'list'
            A list of dictionaries to construct the table from.
        columns: :class:'list'
            A list of dictionary keys of which to construct the table from.
            Each item must match the name of a key in every dictionary contained in dataIn.
        columnsmaxwidth: :class:'dict'
            A dictionary of columns of which the column width is locked.
            These columns will never be truncated.
        maxwidth: :class:'int'
            The maximum width of the outputted table.
            This is measured as the maximum number of characters per line.
        templstr: :class:'Template String'
            This is a template string from which to fill in with data from dataIn.
            Every placeholder in this string must match the name of an item in columns, eg: $character.
        wrapstr: :class:'str'
            An optional arguement to wrap every line in the table with a set of matching characters.
        itemwrap: :class:'dict'
            An optional arguement to wrap table 'cells' in a set of characters before padding them.
        """
        colWidthHrd={}
        colWidthSft={}
        templInp={}
        joinlist=[]
        maxWidth = maxwidth-(len(templstr)-sum([len(x)+1 for x in columns]))
        for x in columns:
            if x in columnsmaxwidth.keys():
                colWidthHrd[x]=columnsmaxwidth[x]
                continue
            for y in dataIn:
                if x in colWidthSft:
                    colWidthSft.update({x: max(len(y[x]), colWidthSft[x])})
                else:
                    colWidthSft.update({x: len(y[x])})
        maxWidth-=sum(colWidthHrd.values())
        if sum(colWidthSft.values()) > maxWidth:
            for x,y in colWidthSft.items():
                if y >= floor(maxWidth/len(colWidthSft)):
                    colWidthSft[x]=floor(maxWidth/len(colWidthSft))
        for x in dataIn:
            for y in columns:
                if y in itemwrap:
                    if y in colWidthSft.keys():
                        tempStr = shorten(str(x[y]), width=colWidthSft[y], expand_tabs=False, break_on_hyphens=False, placeholder=' [...]')
                        wrapMapping = {y: tempStr}
                        wrapTempl = Template(itemwrap[y])
                        tempStr = wrapTempl.substitute(**wrapMapping)
                        tempStr = f"{tempStr:{colWidthSft[y]}}"
                    else:
                        wrapMapping = {y: x[y]}
                        wrapTempl = Template(itemwrap[y])
                        tempStr = wrapTempl.substitute(**wrapMapping)
                        tempStr = f"{tempStr:{colWidthHrd[y]}}"
                else:
                    if y in colWidthSft.keys():
                        tempStr = shorten(str(x[y]), width=colWidthSft[y], expand_tabs=False, break_on_hyphens=False, placeholder=' [...]')
                        tempStr = f"{tempStr:{colWidthSft[y]}}"
                    else:
                        tempStr = f"{x[y]:{colWidthHrd[y]}}"
                templInp[y]=tempStr
            line=Template(templstr)
            if len(wrapstr) == 0:
                joinlist.append(line.substitute(**templInp))
            else:
                joinlist.append(wrapstr+line.substitute(**templInp)+wrapstr)
            templInp.clear()
        return '\n'.join(joinlist)