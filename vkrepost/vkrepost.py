import contextlib
import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from collections import defaultdict
import asyncio
import json
import re
from typing import Optional, List
import vk

CHECK_DELAY = 60

session = vk.Session(access_token='VALID_TOKEN')
api = vk.API(session, v='5.52', lang='ru', timeout=20)
target_id = 138011123

class vkrepost(commands.Cog):
	"""My custom cog"""
	
	
	def __init__(self, bot: Red):
		super().__init__()	
		self.config = Config.get_conf(self, identifier=138011123)

		self.config.register_global(
            LastPostDate = 0,
			LastPostID = 0,
			channel_id = 326018877693755393
        )
		
		self.bot = bot
		self.task = self.bot.loop.create_task(self._check_posts())	
	
	@commands.group()
	@commands.guild_only()
	@checks.admin_or_permissions(manage_guild=True)	
	async def vkr(self, ctx: commands.Context):
		"""Cog Management"""
		pass
		
	@vkr.group(name="repostchan")
	async def chan(self, ctx: commands.Context, channel: str = None):
		"""Set channel for news."""
		if channel is not None:
			await self.config.channel_id.set(channel)
			return
	
	
	async def vkpost(self, ctx: commands.Context, offset: int = 1, bypass: bool = False):
		"""Pulls the last non-pinned post from VK wall"""
		
		id = int("-"+str(target_id))
		channel = int(await self.config.channel_id())
		channel = self.bot.get_channel(channel)
		guild = channel.guild
		response = api.wall.get(owner_id=id, count=1, offset=int(offset), filter='owner')
		print("Checking for new post")
		group = api.groups.getById(group_ids=target_id)
		items = response.get("items")
		lastdate = int(await self.config.LastPostDate())
		lastid = int(await self.config.LastPostID())
		content = ""
		postdate = items[0].get("date")
		postid = items[0].get("id")
		pinned = bool(items[0].get("is_pinned"))
		if pinned is True:
			print("It's a pinned post, canceling")
			return
		
		if (lastdate != 0):
			if lastdate <= postdate:
				if lastid == postid and bypass != True:
					print("Post is up to date, canceling")
					return
		
		print("New post:")
		print("JSON Payload:"+str(response))
		attachments = items[0].get("attachments")
		repost = items[0].get("copy_history")		
		thumb = None
		attachment = None
		title = None
		titleURL = None		
		footer = None
		body = items[0].get("text") 
		body = re.sub('#\S+', '', body) #filter out hashtags
		postURL = "https://vk.com/wall-138011123_"+str(items[0].get("id"))
		

		
		# =======================================
		# Post has attachments, pulling thumbnail
		# =======================================
		if (attachments != None):
			atype = attachments[0].get("type")			
			if atype == 'video':
				attachment = attachments[0].get("video")
				if attachment.get("first_frame_800") != None:
					thumb = str(attachment.get("first_frame_800"))
				elif attachment.get("photo_800") != None:
					thumb = str(attachment.get("photo_800"))
				title = str(attachment.get("title"))
				footer = str(attachment.get("description"))
				
			elif atype == 'photo':
				attachment = attachments[0].get("photo")
				thumb = str(attachment.get("photo_807"))
				
			elif atype == 'link':
				attachment = attachments[0].get("link")
				title = attachments[0].get("title")
				titleURL = attachments[0].get("url")
				
		# =======================================
		# Post is a repost, let's try and pull the link
		# =======================================				
		if (repost != None):
			relink = "https://vk.com/wall"+str(repost[0].get("from_id"))+"_"+str(repost[0].get("id"))
			body = body + "Подробнее: " + relink
			attachments = repost[0].get("attachments")
			atype = attachments[0].get("type")
			if atype == 'video':
				attachment = attachments[0].get("video")
				if attachment.get("first_frame_800") != None:
					thumb = str(attachment.get("first_frame_800"))
				else:
					thumb = str(attachment.get("photo_800"))
				title = str(attachment.get("title"))
				footer = str(attachment.get("description"))
			elif atype == 'photo':
				attachment = attachments[0].get("photo")
				thumb = str(attachment.get("photo_807"))

		
		# make sure the text is short enough to avoid post getting blocked.
		# if longer than 1650, trim to 1650 and add "read more" + link
		if (len(body) > 1650): 
			body = body[:1650]+".../n/nЧитать полностью в ВКонтакте:"+ str(postURL)
		avatar = group[0].get("photo_100")
				
		if titleURL is None:
			titleURL = postURL
		embed=discord.Embed(title=title, url=titleURL, description=body, color=0xba14d8)
		if thumb is not None:
			embed.set_image(url=thumb)
		embed.set_author(name="Fortnite", url=postURL, icon_url=avatar)
		if footer is not None:
			embed.set_footer(text=footer)
		await channel.send(embed=embed)
		await self.config.LastPostDate.set(postdate)
		await self.config.LastPostID.set(postid)
	
	@commands.command()
	@checks.admin_or_permissions(manage_guild=True)	
	async def status(self, ctx: commands.Context):
		await ctx.send("Watching group {}. "
							"Last post date: {}. "
							"Last post id: {}. "
							"Channel ID {}. "
							"Task exists: {}".format(target_id, 
											await self.config.LastPostDate(), 
											await self.config.LastPostID(),
											await self.config.channel_id(),
											str(self.task != None)))

											
	@commands.command()
	@checks.admin_or_permissions(manage_guild=True)	
	async def test(self, ctx: commands.Context, offset: int = 1, bypass: bool = False):
		await self.vkpost(ctx, offset, True)
	
	
	async def _check_posts(self):
		while True:
			await self.vkpost(1, 1)				
			await asyncio.sleep(60)
		

	def __unload(self):
		if self.task:
			self.task.cancel()

	__del__ = __unload