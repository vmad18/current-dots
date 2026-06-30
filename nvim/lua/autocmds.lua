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

local session_dir = vim.fn.stdpath "state" .. "/sessions/by-cwd"

local function cwd_session()
  local cwd = vim.fn.getcwd()
  local name = cwd:gsub("[/\\:]", "%%"):gsub("[^%w%._%-%%]", "_")
  return session_dir .. "/" .. name .. ".vim"
end

vim.opt.sessionoptions = {
  "buffers",
  "curdir",
  "folds",
  "help",
  "localoptions",
  "tabpages",
  "terminal",
  "winsize",
}

vim.api.nvim_create_autocmd("VimEnter", {
  group = vim.api.nvim_create_augroup("last_session_restore", { clear = true }),
  callback = function()
    local session = cwd_session()
    if vim.env.NVIM_NO_SESSION == "1" or vim.fn.argc(-1) > 0 or vim.fn.filereadable(session) == 0 then
      return
    end

    vim.schedule(function()
      vim.cmd("silent! source " .. vim.fn.fnameescape(session))
    end)
  end,
})

vim.api.nvim_create_autocmd("VimLeavePre", {
  group = vim.api.nvim_create_augroup("last_session_save", { clear = true }),
  callback = function()
    if vim.env.NVIM_NO_SESSION == "1" or vim.fn.argc(-1) > 0 or vim.v.dying ~= 0 then
      return
    end

    local session = cwd_session()
    vim.fn.mkdir(vim.fn.fnamemodify(session, ":h"), "p")
    vim.cmd("silent! mksession! " .. vim.fn.fnameescape(session))
  end,
})
