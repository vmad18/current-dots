# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
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

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.

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
export PICO_SDK_PATH="$HOME/Documents/Code/clibs/pi/pico-sdk"
alias ml_env="source '$(echo $ml_env)'"
alias change_bg="sh ~/.config/sys-scripts/background/randbg.sh $1"
alias img_view="sxiv $1"
alias save-style="sh ~/.config/style-change/save_current_state.sh $1"
alias docker="sudo docker"
alias shellm="~/./shellm"
alias vim="nvim"
alias ssh_tuo="TERM=xterm ssh -l madan2 tuo.llnl.gov"

alias strg="df -h ."

cchat() {
  if (( $# == 0 )); then
    echo "Usage: cchat <query>" >&2
    return 2
  fi

  codex --ask-for-approval never exec -m gpt-5.5 -c model_reasoning_effort=\"medium\" \
    --ephemeral --skip-git-repo-check --sandbox read-only -C "$PWD" \
    "Answer this quick shell query concisely. Do not edit files. Query: $*"
}

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
