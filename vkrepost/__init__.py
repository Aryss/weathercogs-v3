from .vkrepost import vkrepost

async def setup(bot):
	bot.add_cog(vkrepost(bot))