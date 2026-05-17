
export ZSH="$HOME/.oh-my-zsh"
export JAVA_HOME="/usr/lib/jvm/java-22-openjdk"

if [[ -f "$HOME/.config/zsh/env.zsh" ]]; then 
  source "$HOME/.config/zsh/env.zsh"
fi


# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="zap-prompt"

source ~/.oh-my-zsh/plugins/supercharge/supercharge.plugin.zsh

plugins=(
	git
	supercharge
	zsh-autosuggestions
	zsh-syntax-highlighting
)

ctheme() {
  sh ~/.config/hypr/scripts/theme_changer.sh $1
}

gvim() {
  if [ $1 ] 
  then
    nohup neovide $1 &> /dev/null &
    disown
  else
    nohup neovide &> /dev/null &
    disown
  fi
  exit
}

source $ZSH/oh-my-zsh.sh
alias fucking="sudo pacman"
alias py_ml="source ml-stuff/bin/activate"
# alias update="sh ~/hypr-dotfiles/update_conf.sh"
# alias gvim="env -u WAYLAND_DISPLAY neovide && exit"
# alias ctheme="sh ~/.config/hypr/scripts/theme_changer.sh $1"
sh ~/.config/sys-scripts/neofetch_bg.sh $(cat ~/.background.md)
# neofetch --source ~/.config/Backgrounds/skelly.jpg --size 250px
# User configuration
ZSH_HIGHLIGHT_STYLES[builtin]='fg=green'
ZSH_HIGHLIGHT_STYLES[function]='fg=green'
ZSH_HIGHLIGHT_STYLES[command]='fg=green'
export ml_env="/home/v18/Documents/Code/ml/ml-env/bin/activate"
alias ml_env="source '$(echo $ml_env)'"
alias change_bg="sh ~/.config/sys-scripts/background/randbg.sh $1"
alias img_view="sxiv $1"
alias save-style="sh ~/.config/style-change/save_current_state.sh $1"
alias docker="sudo docker"
alias shellm="~/./shellm"
alias vim="nvim"
alias ssh_tuo="TERM=xterm ssh -l madan2 tuo.llnl.gov"

alias strg="df -h ."

