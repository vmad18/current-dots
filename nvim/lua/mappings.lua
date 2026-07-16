require "nvchad.mappings"

-- add yours here

local map = vim.keymap.set

if vim.g.neovide then
  local scale_file = vim.fn.stdpath "state" .. "/neovide-scale"

  if vim.fn.filereadable(scale_file) == 1 then
    local saved_scale = tonumber(vim.fn.readfile(scale_file, "", 1)[1])
    if saved_scale and saved_scale >= 0.5 and saved_scale <= 3.0 then
      vim.g.neovide_scale_factor = saved_scale
    end
  end

  local function save_neovide_scale()
    vim.fn.mkdir(vim.fn.fnamemodify(scale_file, ":h"), "p")
    vim.fn.writefile({ string.format("%.6f", vim.g.neovide_scale_factor or 1.0) }, scale_file)
  end

  local function change_neovide_scale(factor)
    local scale = (vim.g.neovide_scale_factor or 1.0) * factor
    vim.g.neovide_scale_factor = math.max(0.5, math.min(scale, 3.0))
    save_neovide_scale()
  end

  local zoom_modes = { "n", "i", "v", "t" }

  map(zoom_modes, "<C-->", function()
    change_neovide_scale(1 / 1.1)
  end, { desc = "Neovide zoom out" })

  map(zoom_modes, "<C-=>", function()
    change_neovide_scale(1.1)
  end, { desc = "Neovide zoom in" })

  map(zoom_modes, "<C-0>", function()
    vim.g.neovide_scale_factor = 1.0
    save_neovide_scale()
  end, { desc = "Reset Neovide zoom" })

  local function paste_from_clipboard()
    vim.api.nvim_paste(vim.fn.getreg "+", true, -1)
  end

  map({ "n", "i", "v", "c", "t" }, "<S-C-v>", paste_from_clipboard, {
    silent = true,
    desc = "Paste from system clipboard",
  })

  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = vim.api.nvim_create_augroup("neovide_scale_save", { clear = true }),
    callback = save_neovide_scale,
  })
end

map("n", ";", ":", { desc = "CMD enter command mode" })
map("i", "jk", "<ESC>")

-- === Custom abc mappings ===
map("n", "<C-1>", "<Home>", { desc = "Go to line start" })
map("n", "<C-2>", "<End>", { desc = "Go to line end" })

-- === Window navigation with Ctrl + Arrow Keys ===
map("n", "<C-Left>", "<C-w>h", { desc = "Move to left window" })
map("n", "<C-Down>", "<C-w>j", { desc = "Move to lower window" })
map("n", "<C-Up>", "<C-w>k", { desc = "Move to upper window" })
map("n", "<C-Right>", "<C-w>l", { desc = "Move to right window" })
-- map({ "n", "i", "v" }, "<C-s>", "<cmd> w <cr>")
