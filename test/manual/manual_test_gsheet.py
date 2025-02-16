# https://docs.google.com/spreadsheets/d/e/2PACX-1vQecDpePfTlrou6IYxeNDV78aBDwLNtdCixT3nwxLX3LUy9alwcIR4qtP09c-YZZs0K7d9GWcBnqHLG/pubhtml
#
#

from ragtrain.mcq import load_qaitems_from_gsheet, aload_qaitems_from_gsheet

# Synchronous usage
sheet_id = "1bLqvjC5UB_4RVkKVWQdfJWk32Rq-SZN7ZXV4DHN8dkA"
items = load_qaitems_from_gsheet(sheet_id)
import pdb; pdb.set_trace()

# # Async usage
# async def fetch_items():
#     items = await aload_qaitems_from_gsheet(sheet_id)