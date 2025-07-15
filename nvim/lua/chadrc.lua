-- This file needs to have same structure as nvconfig.lua 
-- https://github.com/NvChad/ui/blob/v3.0/lua/nvconfig.lua
-- Please read that file to know all available options :( 

---@type ChadrcConfig
local M = {}

M.base46 = {
	theme = "pastelbeans",

	-- hl_override = {
	-- 	Comment = { italic = true },
	-- 	["@comment"] = { italic = true },
	-- },
}


  M.nvdash = {
    load_on_startup = true,

    header = {
      " ███▄    █ ██▒   █▓ ██▓ ███▄ ▄███▓",
      " ██ ▀█   █▓██░   █▒▓██▒▓██▒▀█▀ ██▒",
      "▓██  ▀█ ██▒▓██  █▒░▒██▒▓██    ▓██░",
      "▓██▒  ▐▌██▒ ▒██ █░░░██░▒██    ▒██ ",
      "▒██░   ▓██░  ▒▀█░  ░██░▒██▒   ░██▒",
      "░ ▒░   ▒ ▒   ░ ▐░  ░▓  ░ ▒░   ░  ░",
      "░ ░░   ░ ▒░  ░ ░░   ▒ ░░  ░      ░",
      "   ░   ░ ░     ░░   ▒ ░░      ░   ",
      "         ░      ░   ░         ░   ",
      "               ░                  ",

    },

    -- buttons = {
    --   { "  Find File", "Spc f f", "Telescope find_files" },
    --   { "󰈚  Recent Files", "Spc f o", "Telescope oldfiles" },
    --   { "󰈭  Find Word", "Spc f w", "Telescope live_grep" },
    --   { "  Bookmarks", "Spc m a", "Telescope marks" },
    --   { "  Themes", "Spc t h", "Telescope themes" },
    --   { "  Mappings", "Spc c h", "NvCheatsheet" },
    -- },
  }

-- M.nvdash = { load_on_startup = true }
-- M.ui = {
--       tabufline = {
--          lazyload = false
--      }
--}

return M
