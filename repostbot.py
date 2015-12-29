import praw
import urllib2
import hashlib
import sqlite3
import time

#TODO: fix all TODO statements.


#get_hot(r, sub, num, c, conn)
#returns void
#r = Reddit object (e.g. r = praw.Reddit("Repost checker by /u/Pandemic21"))
#sub = subreddit to check (e.g. "aww")
#num = number of latest posts to check (e.g. 5)
#c = sqlite3 cursor object
#conn = sqlite3 connection object
def get_hot(r, sub, num, c, conn):
	subreddit = r.get_subreddit(sub)

	#get the latest submissions in the subreddit
	for submission in subreddit.get_new(limit=num):
		#check if we have already checked this post
		print "Determining if this post has already been checked..."

		if get_row_exists(c, 'original_submissions', 'permalink', submission.permalink) is True:
			#we have already checked it
			print "Submission " + submission.permalink + " has already been checked, continuing..."
			print '\n'
			continue

		#if we get here this is an unchecked post
		print "Submission unchecked, continuing..."
		
		#convert 
		url_type = get_url_type(submission.url)

		if url_type is "direct":
			print '"' + submission.url + '" is a direct URL, skipping conversion...'
			url = submission.url
		elif url_type is "album":
			#TODO: implement album checking
			print '"' + submission.url + '" is an album, aborting...'
			continue
		elif url_type is "standard":
			print '"' + submission.url + '" is a standard URL, converting...'
			url = convert_to_direct_url(submission.url)
		else:
			#TODO: figure out why it's here
			print 'Submission weird (' + submission.url + '), checking weird_submissions...'
			#if it's NOT already in weird submissions...
			if get_row_exists(c, 'weird_submissions', 'permalink', submission.permalink) is False:
				print 'Not in weird_submissions, dumping to table and continuing...'
				c.execute("INSERT INTO weird_submissions VALUES (?,?,?)", (submission.permalink, submission.title, submission.url,))
				conn.commit()
			#if it is in weird_submissions...
			else:
				print 'Already in weird_submissions, continuing...'
			print '\n'
			continue
		
		#url will be in "i.imgur.com/asdf.jpg" format
		print 'Downloading "' + url + '"'
		download_image(url, saveLocation)
		print 'Checksumming "' + url + '"'
		sha_256_hash = get_sha256_sum(saveLocation)
	
		#check and see if repost. If the hash already exists, it's a repost. 
		if get_row_exists(c, 'original_submissions', 'hash', sha_256_hash) is True:
			#is definitely a repost, but we need to see if we've already alerted this repost...
			if get_row_exists(c, 'repost_submissions', 'hash', sha_256_hash) is False:
				print 'REEEEEEEEEEEEEEEEEEEEPOST! Dumping repost data...'
				print submission.permalink
				print submission.title
				print submission.url

				#get original submission data
				c.execute("SELECT permalink FROM original_submissions WHERE hash=?",(sha_256_hash,))
				original_submission = c.fetchall()

				print 'Dumping original post data...'
				for ele in original_submission:
					print ele

				print 'Adding repost to repost_submissions...'
				c.execute("INSERT INTO repost_submissions VALUES (?,?,?,?)", (submission.permalink, submission.title, submission.url, sha_256_hash,))
				conn.commit()
			
			#if it gets here then it is a repost that we have already alerted to
			else:
				print 'Repost, already alerted. Dumping repost data...'
				c.execute("SELECT permalink FROM repost_submissions WHERE hash=?",(sha_256_hash,))
				repost_submission = c.fetchall()

				print 'Dumping original post data...'
				for ele in repost_submission:
					print ele
					print

		else:
			print submission.url + ' is an original post, adding to database...'
			c.execute("INSERT INTO original_submissions VALUES (?,?,?,?)", (submission.permalink, submission.title, submission.url, sha_256_hash,))
			conn.commit()
			print '\n\n\n'


#download_image(url, img_location)
#void function
#url = direct URL (e.g. "i.imgur.com/asdf.jpg")
#img_location = location you want the image saved (e.g. '/home/user/Downloads/img')
def download_image(url, img_location):
	f = open(img_location, 'w')
	contents=urllib2.urlopen(url)
	f.write(contents.read())
	f.close()

#get_sha256_sum(img_location)
#returns sha256 checksum of a downloaded image
#img_location = location of the saved image (e.g. '/home/user/Downloads/img')
def get_sha256_sum(img_location):
	return hashlib.sha256(open(img_location, 'rb').read()).hexdigest()

#convert_to_direct_url(url)
#returns a direct URL (e.g. "i.imgur.com/asdf.jpg"
#url = standard imgur URL (e.g. "imgur.com/asdf"
def convert_to_direct_url(url):
	url = url.replace('imgur', 'i.imgur')
	#images that end in .gifv make it puke :(. If it's in the URL then just return i.imgur.com/asdf.gifv
	if ".gifv" in url:
		return url
	#doesn't end in .gifv, add .jpg
	url = url + '.jpg'
	return url

#get_url_type(url)
#returns either "direct", "album", or "standard"
#url = submission.url (the URL in the submission)
#"direct" links directly to the image and is ready to be downloaded
#"album" is an album of images
#"standard" is a standard imgur link and can be converted to a direct link
def get_url_type(url):
	if 'i.imgur' in url:
		return "direct"
	elif 'imgur.com/a/' in url:
		return "album"
	elif '/gallery/' in url:
		return 'gallery'
	elif 'imgur.com' in url:
		return "standard"
	else:
		return 'non-imgur'

#get_row_exists(c, permalink)
#returns True if the row exists (e.g. has already been entered in the DB)
#returns False if the row does not exist (e.g. has not been entered into the DB)
#c = sqlite3 cursor (e.g. 'c = conn.cursor()')
#table = the table to query (e.g. "original_submissions" or "repost_submissions")
#permalink = permalink of the submission to check
def get_row_exists(c, table, column, value):
	c.execute("SELECT count(*) FROM "+table+" WHERE "+column+"=?", (value,))
	data = c.fetchone()[0]
	if data==0:
		return False
	else:
		return True

##################################################################################
##################################################################################
##################################################################################

r = praw.Reddit("Repost checker by /u/Pandemic21")
conn = sqlite3.connect('/home/pandemic/Documents/mydb.db')
c = conn.cursor()
saveLocation = '/home/pandemic/Downloads/kitty'

#create tables, if they don't exist
c.execute("CREATE TABLE IF NOT EXISTS original_submissions (permalink text, title text, url text, hash text)")
c.execute("CREATE TABLE IF NOT EXISTS repost_submissions (permalink text, title text, url text, hash text)")
c.execute("CREATE TABLE IF NOT EXISTS weird_submissions (permalink text, title text, url text)")
conn.commit()

while True:
	get_hot(r, 'aww', 10, c, conn)
	time.sleep(30)
	get_hot(r, 'pics', 10, c, conn)
	time.sleep(30)
