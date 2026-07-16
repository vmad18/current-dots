require "nvchad.mappings"

-- add yours here

local map = vim.keymap.set

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
