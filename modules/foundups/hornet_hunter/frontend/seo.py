"""Search metadata grounded in the site's visible content."""

LINKEDIN = 'https://www.linkedin.com/in/openstartup/'
LINKEDIN_ICON = '<svg class="linkedin-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false"><rect width="24" height="24" rx="2" fill="#0a66c2"/><path fill="#fff" d="M5.3 8.7h3.1v10H5.3zm1.55-5a1.8 1.8 0 1 1 0 3.6 1.8 1.8 0 0 1 0-3.6M10.3 8.7h3v1.4h.04c.42-.8 1.44-1.65 2.96-1.65 3.17 0 3.75 2.08 3.75 4.79v5.46h-3.1v-4.84c0-1.16-.02-2.65-1.61-2.65-1.62 0-1.87 1.27-1.87 2.57v4.92H10.3z"/></svg>'

TITLES = {
 '/': ('Hornet Hunter | Giant Hornet Filming in Japan', 'Japan hornet filming with Michael J. Trout (UnDaoDu), consultant on Secrets of the Bees. Documentary field support, locations and shoot coordination.'),
 '/work/secrets-of-the-bees/': ('Secrets of the Bees: Hornet Consultant Michael J. Trout', 'Meet Michael J. Trout, hornet consultant for Silverback Films’ Secrets of the Bees. Explore Japanese honeybee filming and watch the official Nat Geo trailer.'),
 '/work/killer-hornets-from-hell/': ('Killer Hornets from Hell | Michael J. Trout, Hornet Hunter', 'Michael J. Trout’s beekeeping story and Animal Planet documentary work in Killer Hornets from Hell, produced by Hoff Productions. Watch the preview.'),
}

def graph(base, path, title, description, image):
 person = {'@type':'Person','@id':base+'/#michael-trout','name':'Michael J. Trout','alternateName':['Mike Trout','UnDaoDu'],'url':base+'/about/','sameAs':[LINKEDIN],'jobTitle':'Hornet filming consultant'}
 org = {'@type':'Organization','@id':base+'/#organization','name':'Hornet Hunter','url':base+'/','founder':{'@id':person['@id']},'sameAs':['https://www.facebook.com/hornethunters/']}
 website = {'@type':'WebSite','@id':base+'/#website','name':'Hornet Hunter','alternateName':'HornetHunter.com','url':base+'/','publisher':{'@id':org['@id']},'inLanguage':'en'}
 page = {'@type':'WebPage','@id':base+path+'#webpage','url':base+path,'name':title,'description':description,'isPartOf':{'@id':website['@id']},'primaryImageOfPage':{'@type':'ImageObject','url':base+image},'inLanguage':'en'}
 nodes = [org,person,website,page]
 if path != '/':
  crumbs = [{'@type':'ListItem','position':1,'name':'Hornet Hunter','item':base+'/'}]
  if path.startswith('/work/') and path != '/work/':
   crumbs.append({'@type':'ListItem','position':2,'name':'Documentary work','item':base+'/work/'})
  elif path.startswith('/journal/') and path != '/journal/':
   crumbs.append({'@type':'ListItem','position':2,'name':'Field notes','item':base+'/journal/'})
  crumbs.append({'@type':'ListItem','position':len(crumbs)+1,'name':title.split(' | ')[0],'item':base+path})
  nodes.append({'@type':'BreadcrumbList','@id':base+path+'#breadcrumbs','itemListElement':crumbs})
  page['breadcrumb'] = {'@id':base+path+'#breadcrumbs'}
 if path == '/about/':
  page['@type']='ProfilePage';page['mainEntity']={'@id':person['@id']}
 if path == '/filming/':
  nodes.append({'@type':'Service','@id':base+path+'#service','name':'Giant hornet filming support in Japan','serviceType':'Documentary field consultancy and shoot coordination','provider':{'@id':org['@id']},'areaServed':{'@type':'Country','name':'Japan'},'url':base+path})
  page['mainEntity']={'@id':base+path+'#service'}
 if path == '/work/secrets-of-the-bees/':
  nodes.append({'@type':'TVSeries','@id':base+path+'#series','name':'Secrets of the Bees','productionCompany':{'@type':'Organization','name':'Silverback Films'},'url':'https://silverbackfilms.tv/shows/secrets-of-the-bees/'})
  page['about']=[{'@id':base+path+'#series'},{'@id':person['@id']}]
 return {'@context':'https://schema.org','@graph':nodes}
