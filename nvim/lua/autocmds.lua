require "nvchad.autocmds"

local themes_by_filetype = {
  c = "rosepine",
  cpp = "rosepine",
  kotlin = "catppuccin",
  python = "pastelbeans",
  rust = "gruvbox",
}

vim.g.filetype_theme_enabled = vim.g.filetype_theme_enabled ~= false

local function apply_filetype_theme()
  if not vim.g.filetype_theme_enabled then
    return
  end

  local theme = themes_by_filetype[vim.bo.filetype]
  if not theme then
    return
  end

  local base46_config = require("nvconfig").base46
  if base46_config.theme == theme then
    return
  end

  base46_config.theme = theme
  require("base46").load_all_highlights()
end

vim.api.nvim_create_autocmd({ "BufEnter", "FileType" }, {
  group = vim.api.nvim_create_augroup("filetype_theme", { clear = true }),
  callback = apply_filetype_theme,
})

vim.api.nvim_create_user_command("CodeTheme", function()
  vim.g.filetype_theme_enabled = not vim.g.filetype_theme_enabled

  if vim.g.filetype_theme_enabled then
    apply_filetype_theme()
    vim.notify "Filetype themes enabled"
  else
    vim.notify "Filetype themes disabled"
  end
end, {
  desc = "Toggle filetype-based theme switching",
})
