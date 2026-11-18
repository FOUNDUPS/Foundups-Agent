"""Generate bounded native FIN updates from repository-owned planning assumptions.

No network writes. Emits JSON batches for the authorized Google Sheets connector.
Existing site identities, grant ledger, legacy model and deployment gates survive.
"""
import json
import sys
from pathlib import Path
from .yumori_planning_scenarios import load_planning_assumptions, cost_site, run_planning_scenario

BOOK = '1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0'
IDS = {'Dashboard':2001,'Assumptions':2002,'CapEx':2003,'Revenue':2004,'Opex':2005,'Financing':2006,'5Y Model':2007,'Sensitivity':2008,'Audit & Checks':2009,'Site 1 — Sukatto':1415326634,'Site 2 — Shimousaka':1202403590,'Site 3 — Hanyu':1103579412}

def cell(v):
    if v is None:return {}
    if isinstance(v,(float,int)):return {'userEnteredValue':{'numberValue':v}}
    return {'userEnteredValue':{'formulaValue' if v.startswith('=') else 'stringValue':v}}

def build_projection():
    data=load_planning_assumptions(); batches={}; req=[]
    def put(tab,row,rows,col=0):
        req.append({'updateCells':{'start':{'sheetId':IDS[tab],'rowIndex':row-1,'columnIndex':col},'rows':[{'values':[cell(v) for v in r]} for r in rows],'fields':'userEnteredValue'}})
    def finish(name):batches[name]={'spreadsheet_id':BOOK,'requests':req.copy()};req.clear()
    def style(tab,r1,r2,c1=0,c2=6):
        req.append({'repeatCell':{'range':{'sheetId':IDS[tab],'startRowIndex':r1-1,'endRowIndex':r2,'startColumnIndex':c1,'endColumnIndex':c2},'cell':{'userEnteredFormat':{'wrapStrategy':'WRAP','verticalAlignment':'TOP','textFormat':{'fontFamily':'Arial','fontSize':10}}},'fields':'userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat'}})
        req.append({'autoResizeDimensions':{'dimensions':{'sheetId':IDS[tab],'dimension':'ROWS','startIndex':r1-1,'endIndex':r2}}})
    put('Assumptions',68,[['COSTED PLANNING CASE — ALL PROJECT INPUTS MODEL ONLY','Value','Unit','Basis / exclusion']])
    h,s=data['sites'][:2]
    inputs=[('Hours/year',data['hours_per_year'],'h','365-day convention'),('GPUs/server',data['gpus_per_node'],'GPU','S2 specification comparator'),('Maximum server input',data['node_max_kw'],'kW','S2; not measured project equipment'),('Service availability',data['availability'],'fraction','MODEL ONLY'),('Idle power/max power',data['idle_power_fraction'],'fraction','MODEL ONLY; idle energy is not zero'),('Hanyu design demand',h['design_peak_gpu_hours'],'GPUh/year','Assumed peak demand, NOT contracted'),('Hanyu design utilization',h['design_utilization'],'fraction','MODEL ONLY'),('Hanyu other IT',h['other_it_kw'],'kW','MODEL ONLY network/storage'),('Hanyu PUE',h['pue'],'ratio','MODEL ONLY, unengineered'),('Hanyu server count','=ROUNDUP(B74/(B69*B75*B70),0)','servers','Demand-derived scenario only'),('Hanyu GPUs','=B78*B70','GPU','Not installed/ordered'),('Hanyu peak facility power','=(B78*B71+B76)*B77','kW','Required scenario load, NOT available capacity'),('Shimousaka design demand',s['design_peak_gpu_hours'],'GPUh/year','Independent assumption, NOT contracted'),('Shimousaka design utilization',s['design_utilization'],'fraction','MODEL ONLY'),('Shimousaka other IT',s['other_it_kw'],'kW','Independent MODEL ONLY'),('Shimousaka PUE',s['pue'],'ratio','Independent MODEL ONLY'),('Shimousaka server count','=ROUNDUP(B81/(B69*B82*B70),0)','servers','Demand-derived scenario only'),('Shimousaka GPUs','=B85*B70','GPU','Not installed/ordered'),('Shimousaka peak facility power','=(B85*B71+B83)*B84','kW','Required scenario load, NOT available capacity'),('Additional Hanyu expansion',0,'JPY','Explicitly excluded; new demand/cost tranche required')]
    put('Assumptions',69,[list(x) for x in inputs])
    keys=['price_jpy_gpu_hour','price_escalation','energy_jpy_kwh','demand_charge_jpy_kw_month','energy_escalation','operations_y1_jpy','operations_escalation','variable_opex_share','maintenance_share_capex','tax_rate','working_capital_share','renewal_fraction_year5','debt_share','debt_rate','debt_term_years','reserve_share_capex','investor_return_rate','investor_repayment_years','community_y1_jpy','compute_life_years','infrastructure_life_years']
    put('Assumptions',90,[['Independent scenario inputs','Downside','Base','Upside','Basis']])
    for row,key in enumerate(keys,91):
        put('Assumptions',row,[[key.replace('_',' ')]+[data['scenarios'][n][key] for n in ('downside','base','upside')]+['MODEL ONLY']])
    put('Assumptions',114,[['Basis / source','Verified comparator only; ALL site construction costs remain MODEL ONLY']])
    for row,source in enumerate(data['sources'],115):put('Assumptions',row,[[source['id'],source['url'],source['fact']]])
    put('Assumptions',119,[['Tax / currency',data['tax_basis']],['Scope','No demolition saving, building valuation, heat sale or unawarded grant counted as project cash.'],['Financing','Debt/equity below are hypothetical financing obligations; committed-source ledger stays zero.'],['Evidence','INSUFFICIENT EVIDENCE — assumptions complete does not mean utility/demand/quotes verified.']])
    style('Assumptions',68,122,0,5);finish('01_assumptions')
    for site in data['sites']:
        tab=site['site_id']+' — '+site['name']; costs=cost_site(site,data,'base'); end=14+len(costs)
        put(tab,14,[['Cost component','Base JPY','Evidence class','Scope / basis','Quantity','Base unit JPY / rate','Low JPY','High JPY']])
        for r,c in enumerate(costs,15):
            qty=c['resolved_quantity']; rates=c['unit_cost_jpy']
            if c['category']=='contingency':
                compute_row=next((15+i for i,x in enumerate(costs) if x['category'] in ('compute_hardware','optional_compute')),0)
                def basis(col):return '+'.join(f'{col}{i}' for i in range(15,end+1) if i not in (r,compute_row))
                qty='='+basis('B');lo='=('+basis('G')+')*'+str(rates['low']);hi='=('+basis('H')+')*'+str(rates['high'])
            else:
                if c.get('quantity')=='demand_nodes':qty='=Assumptions!B'+('78' if site['site_id']=='Site 3' else '85')
                lo=f'=E{r}*{rates["low"]}';hi=f'=E{r}*{rates["high"]}'
            put(tab,r,[[c['category'].replace('_',' '),f'=E{r}*F{r}','MODEL ONLY',c['scope']+'; unit: '+c['unit'],qty,rates['base'],lo,hi]])
        put(tab,35,[['Planning subtotal — not quote']]);put(tab,37,[['Complete numeric planning CapEx']]);put(tab,38,[['Evidence remains unresolved','All 50 site cost lines are MODEL ONLY; high/low are sensitivity bounds, not guaranteed cost limits.']])
        invalid=f'=COUNTIF(B15:B{end},"<0")+COUNTIF(G15:H{end},"<0")+COUNTIFS(B15:B{end},">=0",C15:C{end},"TBD")'
        for evidence in ('SOURCED','VENDOR QUOTE','ENGINEERING ESTIMATE'):
            invalid+=f'+COUNTIFS(C15:C{end},"{evidence}",D15:D{end},"TBD")+COUNTIFS(C15:C{end},"{evidence}",D15:D{end},"")'
        put(tab,39,[[invalid]],1)
        style(tab,14,end,0,8)
        req.append({'repeatCell':{'range':{'sheetId':IDS[tab],'startRowIndex':14,'endRowIndex':end,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}})
    put('CapEx',25,[['Priority 1 expansion','Excluded from this initial-three-site scope','=Assumptions!B88']],0)
    put('CapEx',26,[['Total modeled portfolio','MODEL ONLY — not approved budget']],0)
    put('CapEx',27,[['Cost interpretation','Planning allowances now populate every cost line. No site/vendor/utility quote is implied; demand and all deployment gates remain unverified.']])
    put('CapEx',32,[['Selected portfolio — planning ranges','Low JPY','Base JPY','High JPY']])
    for r,site in enumerate(data['sites'],33):
        tab=site['site_id']+' — '+site['name'];end=14+len(cost_site(site,data,'base'))
        put('CapEx',r,[[tab,f'=IF(\'{tab}\'!B12,SUM(\'{tab}\'!G15:G{end}),0)',f'=IF(\'{tab}\'!B12,\'{tab}\'!B37,0)',f'=IF(\'{tab}\'!B12,SUM(\'{tab}\'!H15:H{end}),0)']])
    put('CapEx',36,[['Hanyu additional expansion','=C25','=C25','=C25'],['Total portfolio','=SUM(B33:B36)','=SUM(C33:C36)','=SUM(D33:D36)'],['Range meaning','Same bounded scope, low/base/high allowances. High is not a guaranteed maximum.'],['All amounts','Nominal JPY ex consumption tax; VAT timing, escalation to construction date and larger utility scope remain unresolved.']])
    style('CapEx',32,39,0,4);finish('02_capex')
    for name,ac,cc,cr,rr,op,start in [('downside','B','D','H',30,30,35),('base','C','C','B',45,65,80),('upside','D','B','G',60,100,125)]:
        terms=data['scenarios'][name];a=lambda r:f'Assumptions!${ac}${r}'
        cap=f'CapEx!${cc}$33';compute=f"'Site 3 — Hanyu'!${cr}$21"
        put('Revenue',rr,[[name+' — assumed Hanyu demand','Year 1','Year 2','Year 3','Year 4','Year 5']])
        put('Revenue',rr+1,[['Assumed sold GPU-hours']+terms['gpu_hours']])
        for off,label in [(2,'Realized price ex tax / GPUh'),(3,'Available annual GPU-hours'),(4,'Sold utilization'),(5,'Compute revenue'),(6,'Capacity guard')]:
            formulas=[]
            for y,col in enumerate('BCDEF'):
                forms={2:f'{a(91)}*(1+{a(92)})^{y}',3:'Assumptions!$B$79*Assumptions!$B$69*Assumptions!$B$72',4:f'{col}{rr+1}/(Assumptions!$B$79*Assumptions!$B$69)',5:f'{col}{rr+1}*{col}{rr+2}',6:f'IF(AND({col}{rr+1}>=0,{col}{rr+1}<={col}{rr+3}),"PASS SCENARIO","FAIL CAPACITY")'}
                formulas.append('='+forms[off])
            put('Revenue',rr+off,[[label]+formulas])
        put('Revenue',rr+8,[['Evidence','MODEL ONLY hypothetical customer-hours. No order, realized price or available utility capacity is established.']])
        labels=['Annual facility energy kWh','Energy charge','Demand charge','Electricity total','Operations / carrier / rent / insurance','Maintenance expense','Community cash','EBITDA','Opening scenario debt','Interest','Principal repayment','Closing debt','Depreciation proxy','Cash tax proxy','Working capital target','Peak working capital','Working capital cash increase','Equipment renewal CapEx','Reserve contribution','Investor due: return + capital','Debt service','Cash before debt / CFADS']
        put('Opex',op,[[name+' — full cash drivers','Year 1','Year 2','Year 3','Year 4','Year 5']])
        for off,label in enumerate(labels,1):
            fs=[]
            for y,col in enumerate('BCDEF'):
                prev=chr(ord(col)-1); rev=f'Revenue!{col}{rr+5}';power=f'(Assumptions!$B$78*Assumptions!$B$71*(Assumptions!$B$73+(1-Assumptions!$B$73)*Revenue!{col}{rr+4})+Assumptions!$B$76)*Assumptions!$B$77*Assumptions!$B$69'
                forms={1:power,2:f'{col}{op+1}*{a(93)}*(1+{a(95)})^{y}',3:f'ROUNDUP(Assumptions!$B$80,0)*{a(94)}*12',4:f'{col}{op+2}+{col}{op+3}',5:f'{a(96)}*(1+{a(97)})^{y}+{rev}*{a(98)}',6:f'{cap}*{a(99)}',7:a(109),8:f'{rev}-{col}{op+4}-{col}{op+5}-{col}{op+6}-{col}{op+7}',9:f'{cap}*{a(103)}' if y==0 else f'{prev}{op+12}',10:f'{col}{op+9}*{a(104)}',11:f'MIN({col}{op+9},{cap}*{a(103)}/{a(105)})',12:f'{col}{op+9}-{col}{op+11}',13:f'IF({y}<{a(110)},{compute}/{a(110)},0)+IF({y}<{a(111)},({cap}-{compute})/{a(111)},0)',14:f'MAX(0,{col}{op+8}-{col}{op+13}-{col}{op+10})*{a(100)}',15:f'{rev}*{a(101)}',16:f'MAX($B{op+15}:{col}{op+15})',17:f'{col}{op+16}' if y==0 else f'MAX(0,{col}{op+16}-{prev}{op+16})',18:f'{compute}*{a(102)}' if y==4 else '0',19:f'{cap}*{a(106)}',20:f'{cap}*(1-{a(103)})*({a(107)}+IF({y}<{a(108)},1/{a(108)},0))',21:f'{col}{op+10}+{col}{op+11}',22:f'{col}{op+8}-{col}{op+14}-{col}{op+17}-{col}{op+18}'}
                fs.append('='+forms[off])
            put('Opex',op+off,[[label]+fs])
        put('Opex',op+24,[['Scope','MODEL ONLY terms; no debt/equity commitment. Tax proxy excludes loss carryforwards; renewal charged in Year 5; no terminal value.']])
        cash_sources=[('Revenue',rr+5),('Opex',op+4),('Opex',op+5),('Opex',op+6),('Opex',op+14),('Opex',op+17),('Opex',op+18),('Opex',op+21),('Opex',op+19),('Opex',op+20),('Opex',op+7)]
        for off,(source,r) in enumerate(cash_sources,1):put('5Y Model',start+off,[['='+source+'!'+col+str(r) for col in 'BCDEF']],1)
        put('5Y Model',start+15,[['CFADS — cash before debt service']])
        put('5Y Model',start+36,[[f'={cap}*(1-{a(103)})']],1)
        put('5Y Model',start+37,[[f'MODEL ONLY — {terms["cost_case"]} costs; Assumptions 68:122, Revenue and Opex schedules.']],1)
        verdict=f'=IF(OR(NOT(\'Site 3 — Hanyu\'!B12),COUNTIF(Revenue!B{rr+6}:F{rr+6},"FAIL*")>0,CapEx!E26>0,COUNT(B{start+1}:F{start+11})<>55,COUNTIF(B{start+1}:F{start+11},"<0")>0,Financing!B64>0),"INSUFFICIENT EVIDENCE",IF(OR(G{start+28}>0,G{start+29}>0),"NO — ADDITIONAL CAPITAL REQUIRED",IF(G{start+27}>=CapEx!{cc}37-{cap},"YES UNDER CURRENT MODEL ASSUMPTIONS",IF(G{start+27}>0,"PARTIAL SELF-FUNDING","NO — ADDITIONAL CAPITAL REQUIRED"))))'
        put('5Y Model',start+30,[[verdict]],6)
        initial=f'MAX(0,{cap}-Financing!G34)';future=f'MAX(0,CapEx!{cc}34-Financing!G35)+MAX(0,CapEx!{cc}35-Financing!G36)+CapEx!{cc}36'
        put('5Y Model',start+31,[[f'={initial}+MAX(0,{future}-G{start+27})+G{start+28}+G{start+29}']],6)
        # Preserve payback formula shape while switching its cost to this scenario.
        m=f'MATCH(TRUE,ARRAYFORMULA(B{start+24}:F{start+24}>={cap}),0)'
        put('5Y Model',start+34,[[f'=IFERROR({m}-1+({cap}-IF({m}=1,0,INDEX(B{start+24}:F{start+24},1,{m}-1)))/INDEX(B{start+15}:F{start+15},1,{m}),"NOT RECOVERED IN 5 YEARS")']],6)
        style('Revenue',rr,rr+8);style('Opex',op,op+24)
    finish('03_cash')
    for site in data['sites'][1:]:
        tab=site['site_id']+' — '+site['name'];terms=data['later_site_cash'][site['site_id']]
        put(tab,61,[['Independent phase cash — BASE MODEL ONLY','Year 1','Year 2','Year 3','Year 4','Year 5']])
        put(tab,62,[['Assumed GPU-hours' if site['site_id']=='Site 2' else 'Assumed visits']+terms.get('gpu_hours',terms.get('visits'))])
        for off,label in [(2,'Price / GPUh or spend / visit'),(3,'Revenue'),(4,'Electricity / combined variable Opex'),(5,'Fixed + remaining operating cost'),(6,'Maintenance'),(7,'Depreciation proxy'),(8,'Tax proxy'),(9,'Working capital target'),(10,'Working capital cash increase'),(11,'Equipment renewal'),(12,'Cash before debt / CFADS')]:
            vals=[]
            for y,col in enumerate('BCDEF'):
                prev=chr(ord(col)-1)
                if site['site_id']=='Site 2':
                    price=f'{terms["price_jpy_gpu_hour"]}*(1+({terms["price_escalation"]}))^{y}'
                    electricity=f'(Assumptions!$B$85*Assumptions!$B$71*(Assumptions!$B$73+(1-Assumptions!$B$73)*{col}62/(Assumptions!$B$86*Assumptions!$B$69))+Assumptions!$B$83)*Assumptions!$B$84*Assumptions!$B$69*Assumptions!$C$93*(1+Assumptions!$C$95)^{y}+ROUNDUP(Assumptions!$B$87,0)*Assumptions!$C$94*12'
                    operating=f'{terms["operations_y1_jpy"]}*(1+{terms["operations_escalation"]})^{y}+{col}64*Assumptions!$C$98'
                    dep='$B$21/Assumptions!$C$110+($B$37-$B$21)/Assumptions!$C$111';renew='$B$21*Assumptions!$C$102' if y==4 else '0'
                else:
                    price=str(terms['revenue_per_visit_jpy']);electricity=f'{col}64*{terms["variable_opex_share"]}'
                    operating=f'{terms["fixed_opex_y1_jpy"]}*(1+{terms["operations_escalation"]})^{y}'
                    dep='$B$37/Assumptions!$C$111';renew='0'
                forms={2:price,3:f'{col}62*{col}63',4:electricity,5:operating,6:'$B$37*Assumptions!$C$99',7:dep,8:f'MAX(0,{col}64-{col}65-{col}66-{col}67-{col}68)*Assumptions!$C$100',9:f'{col}64*Assumptions!$C$101',10:f'{col}70' if y==0 else f'MAX(0,{col}70-MAX($B70:{prev}70))',11:renew,12:f'{col}64-SUM({col}65:{col}67)-{col}69-{col}71-{col}72'}
                vals.append('='+forms[off])
            put(tab,61+off,[[label]+vals])
        put(tab,53,[[f'={col}73' for col in 'BCDEF']],1)
        put(tab,75,[['Timing boundary','Standalone operating years 1–5; not synchronized construction dates or authority to deploy. No later-site cash is counted toward Hanyu self-funding.']])
        style(tab,61,75)
    put('Dashboard',4,[['PLANNING: can Hanyu fund later phases?']])
    put('Dashboard',5,[['Base modeled portfolio CapEx']]);put('Dashboard',10,[['Planning total — MODEL ONLY']])
    put('Dashboard',43,[['Payback boundary','Standalone site operating years; simultaneous Year-1 portfolio comparison is illustrative only, not a phased drawdown schedule.']])
    put('Dashboard',46,[['Planning case — not forecast','Modeled self-funding','Retained cash JPY','Capital + liquidity screen','Blank annual inputs']])
    put('Dashboard',52,[['EVIDENCE / INVESTMENT READINESS','INSUFFICIENT EVIDENCE'],['Cost confidence','All 50 site lines are MODEL ONLY. No utility response, vendor quote or construction survey establishes these amounts.'],['Not a full-campus budget','Selected phase areas only. Unknown utility/asbestos/structural conditions can invalidate or exceed every case.'],['Financing interpretation','Hypothetical debt and investor obligations are modeled. No commitment, grant award, demolition cash or terminal value is booked.']])
    put('Audit & Checks',48,[['Costed scenarios remain MODEL ONLY','=COUNTIF(\'Site 3 — Hanyu\'!C15:C33,"MODEL ONLY")+COUNTIF(\'Site 2 — Shimousaka\'!C15:C33,"MODEL ONLY")+COUNTIF(\'Site 1 — Sukatto\'!C15:C26,"MODEL ONLY")','EVIDENCE HOLD'],['Unverified capacity preserved','=AND(\'Site 3 — Hanyu\'!B48="TBD",\'Site 2 — Shimousaka\'!B48="TBD")','=IF(B49,"PASS","REVIEW EVIDENCE")'],['Scenario demand capacity','=COUNTIF(Revenue!B36:F36,"FAIL*")+COUNTIF(Revenue!B51:F51,"FAIL*")+COUNTIF(Revenue!B66:F66,"FAIL*")','=IF(B50=0,"PASS","FAIL")']])
    style('Dashboard',52,55,0,2);style('Audit & Checks',48,50,0,3)
    put('Dashboard',4,[['Investment readiness','INSUFFICIENT EVIDENCE']],3)
    put('Dashboard',5,[['Cost lines without quotes','=COUNTIF(\'Site 3 — Hanyu\'!C15:C33,"MODEL ONLY")+COUNTIF(\'Site 2 — Shimousaka\'!C15:C33,"MODEL ONLY")+COUNTIF(\'Site 1 — Sukatto\'!C15:C26,"MODEL ONLY")']],3)
    put('Audit & Checks',36,[['Blank/invalid numeric cost inputs','=CapEx!E26','=IF(B36=0,"NUMERIC COMPLETE","HOLD")','Complete numbers are MODEL ONLY; evidence hold remains below.']])
    for start in (35,80,125):
        put('5Y Model',start+32,[['Blank/invalid cost inputs']])
        req.append({'repeatCell':{'range':{'sheetId':2007,'startRowIndex':start+35,'endRowIndex':start+36,'startColumnIndex':1,'endColumnIndex':2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}})
    headers=[('Assumptions',68,4),('Assumptions',90,5),('CapEx',32,4)]+[(site['site_id']+' — '+site['name'],14,8) for site in data['sites']]+[('Revenue',r,6) for r in (30,45,60)]+[('Opex',r,6) for r in (30,65,100)]+[(site['site_id']+' — '+site['name'],61,6) for site in data['sites'][1:]]
    for tab,row,endcol in headers:
        req.append({'repeatCell':{'range':{'sheetId':IDS[tab],'startRowIndex':row-1,'endRowIndex':row,'startColumnIndex':0,'endColumnIndex':endcol},'cell':{'userEnteredFormat':{'backgroundColor':{'red':.08,'green':.22,'blue':.33},'textFormat':{'bold':True,'foregroundColor':{'red':1,'green':1,'blue':1}}}},'fields':'userEnteredFormat.backgroundColor,userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.foregroundColor'}})
    for tab,r1,r2,c1,c2 in [('CapEx',33,37,1,4),('Opex',31,54,1,6),('Opex',66,89,1,6),('Opex',101,124,1,6)]+[(site['site_id']+' — '+site['name'],15,14+len(cost_site(site,data,'base')),5,8) for site in data['sites']]:
        req.append({'repeatCell':{'range':{'sheetId':IDS[tab],'startRowIndex':r1-1,'endRowIndex':r2,'startColumnIndex':c1,'endColumnIndex':c2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':'#,##0'}}},'fields':'userEnteredFormat.numberFormat'}})
    style('Dashboard',4,4,3,5)
    req.append({'repeatCell':{'range':{'sheetId':2001,'startRowIndex':3,'endRowIndex':4,'startColumnIndex':3,'endColumnIndex':5},'cell':{'userEnteredFormat':{'backgroundColor':{'red':.93,'green':.93,'blue':.93}}},'fields':'userEnteredFormat.backgroundColor'}})
    for tab in ('Assumptions','Revenue','Opex'):
        for first,last,width in [(0,1,280),(1,6 if tab!='Assumptions' else 4,155)]:
            req.append({'updateDimensionProperties':{'range':{'sheetId':IDS[tab],'dimension':'COLUMNS','startIndex':first,'endIndex':last},'properties':{'pixelSize':width},'fields':'pixelSize'}})
    req.append({'updateDimensionProperties':{'range':{'sheetId':2002,'dimension':'COLUMNS','startIndex':4,'endIndex':5},'properties':{'pixelSize':240},'fields':'pixelSize'}})
    formats=[('Assumptions',91,111,1,4,'#,##0.00'),('Revenue',31,35,1,6,'#,##0'),('Revenue',46,50,1,6,'#,##0'),('Revenue',61,65,1,6,'#,##0')]+[(site['site_id']+' — '+site['name'],62,73,1,6,'#,##0') for site in data['sites'][1:]]
    formats += [('Assumptions',r,r,1,4,'0.0%') for r in (92,95,97,98,99,100,101,102,103,104,106,107)]
    formats += [('Revenue',r,r,1,6,'0.0%') for r in (34,49,64)]
    formats += [('Revenue',r,r,1,6,'#,##0.00') for r in (32,47,62)]
    for tab,r1,r2,c1,c2,pattern in formats:
        req.append({'repeatCell':{'range':{'sheetId':IDS[tab],'startRowIndex':r1-1,'endRowIndex':r2,'startColumnIndex':c1,'endColumnIndex':c2},'cell':{'userEnteredFormat':{'numberFormat':{'type':'NUMBER','pattern':pattern}}},'fields':'userEnteredFormat.numberFormat'}})
    for tab,r1,r2 in [('Assumptions',68,122),('Revenue',30,68),('Opex',30,124)]:
        req.append({'autoResizeDimensions':{'dimensions':{'sheetId':IDS[tab],'dimension':'ROWS','startIndex':r1-1,'endIndex':r2}}})
    finish('04_outputs')
    return batches


def markdown_tables():
    data=load_planning_assumptions();lines=['## Costed planning cases — 2026-09-29','',
      '**MODEL ONLY — not quotes, confirmed demand, available utility capacity or secured financing.**',
      'All amounts below are nominal JPY millions, excluding consumption tax. The high case is not a guaranteed upper bound. Selected fit-out areas are hypothetical phase scope, not measured building areas. Additional Hanyu expansion is explicitly excluded (zero) pending a separate costed tranche.','']
    for site in data['sites']:
        rows={k:cost_site(site,data,k) for k in ('low','base','high')}
        lines += [f'### Priority {site["priority"]} — {site["name"]} ({site["site_id"]})','', '| Component | Quantity / unit | Low ¥m | Base ¥m | High ¥m | Scope / status |','| --- | --- | ---: | ---: | ---: | --- |']
        for i,c in enumerate(rows['base']):
            qty='non-compute direct subtotal' if c['category']=='contingency' else f'{c["resolved_quantity"]:g} {c["unit"]}'
            lines.append('| '+ ' | '.join([c['category'],qty]+[f'{rows[k][i]["amount_jpy"]/1e6:,.3f}' for k in ('low','base','high')]+['MODEL ONLY; '+c['scope']])+' |')
        lines.append('| **Total** | | '+' | '.join(f'**{sum(c["amount_jpy"] for c in rows[k])/1e6:,.3f}**' for k in ('low','base','high'))+' | Planning subtotal |');lines.append('')
    lines += ['### Hanyu cash and portfolio funding screen','','| Case | Portfolio CapEx ¥m | Hanyu CapEx ¥m | Y1 revenue ¥m | Y1 EBITDA ¥m | 5y investor paid ¥m | Retained ¥m | Capital + liquidity screen ¥m | Result |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for name in ('downside','base','upside'):
        p=run_planning_scenario(name);r=p['result'];nums=[r['total_portfolio_capex_jpy'],r['site_capex_jpy']['Site 3'],p['annual'][0]['cash']['revenue_jpy'],r['years'][0]['ebitda_jpy'],sum(y['investor_distribution_jpy'] for y in r['years']),r['reinvestable_cash_jpy'],r['residual_financing_gap_jpy']]
        lines.append('| '+name+' | '+' | '.join(f'{n/1e6:,.3f}' for n in nums)+' | '+r['self_funding_result']+' |')
    lines += ['', 'The screen includes initial uncommitted Hanyu capital, the remaining later-site capital after retained cash, peak liquidity and unpaid investor obligations. It is not an accounting cost total or a dated financing drawdown. Scenario debt/equity are hypothetical obligations and do not reduce the committed financing gap. Initial Hanyu capital is still required even in a successful later-site self-funding case.', '', '### Formula and scope audit','',
      '- Demand scenario → discrete 8-GPU servers → IT power → PUE → required facility power. Hanyu: assumed peak 360,000 GPUh at 75% design utilization gives 7 servers / 56 GPUs / 104.49 kW required facility load. Shimousaka: independent 200,000 GPUh at 70% gives 5 servers / 40 GPUs / 85.55 kW. These are calculated planning loads, never utility-confirmed capacity or build decisions.',
      '- Hanyu downside/base/upside prices are ¥340/550/800 per GPU-hour ex tax, with annual changes −5%/−3%/0%. Quantities, prices, electricity and funding terms remain editable MODEL ONLY inputs. Price × sold hours is the only compute revenue; no duplicate managed-service revenue is added.',
      '- Electricity includes idle consumption, PUE, energy-price escalation and peak demand charges. Staffing/carrier/rent/insurance/admin are in fixed Opex; variable platform costs, maintenance and community cash are separate.',
      '- Straight-line debt principal plus declining interest, positive-income tax proxy after depreciation/interest, incremental working capital, Year-5 hardware renewal, reserves, investor preferred return and capital repayment are explicit. Negative operating cash and investor arrears carry forward. No loss-carryforward tax benefit, terminal resale proceeds or released working capital is credited.',
      '- Investor dues assume repayment over five years plus the scenario annual preferred return on initial equity; this is a stress-test obligation, not an agreed term sheet. Paid distributions and retained cash cannot be counted twice.',
      '- Contingency applies once to all non-compute direct costs, including fees. Container shell, receiving cables, transformer, utility works, cooling and compute have mutually exclusive scopes. No legacy Sukatto CapEx is copied into the schools.',
      '- Later-site cash is independently modeled for standalone phase payback. Sukatto visits/spend are hypothetical, not historical demand transferred into a forecast. Its combined variable Opex includes energy; no intersite heat sales, BESS sales or demolition savings are booked.',
      '- Paybacks use supplied operating-year cash only; no recovery within five years is reported as not recovered, not extrapolated. A simultaneous operating-year portfolio comparison is not a construction schedule. Hanyu self-funding never uses later-site cash.',
      '- Confirmed demand, utility/fiber, survey quantities, legal/use terms, tax/VAT treatment, construction timing, lending and offtake remain unresolved. Deployment gates stay HOLD; evidence result stays INSUFFICIENT EVIDENCE despite complete numeric assumptions.', '', '### Primary comparator sources (checked 2026-09-29)','']
    for s in data['sources']:lines.append(f'- [{s["id"]}]({s["url"]}): {s["fact"]}')
    lines += ['', 'Source of inputs: `data/yumori_planning_assumptions.json`. Calculation: `run_planning_scenario()` exposed by the canonical economic module. Native FIN projection: `python -m modules.foundups.esingularity.src.yumori_fin_projection <output-directory>`. Generated native requests require current metadata/range verification before authorized connector writes. No new workbook or alternate model is created.','']
    return '\n'.join(lines)

if __name__=='__main__':
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
    for name,payload in build_projection().items():(out/(name+'.json')).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    (out/'planning_tables.md').write_text(markdown_tables(),encoding='utf-8')
    (out/'expected.json').write_text(json.dumps({n:run_planning_scenario(n) for n in ('downside','base','upside')},ensure_ascii=False),encoding='utf-8')
    print('Generated four native batches, canonical document tables and calculation evidence.')
