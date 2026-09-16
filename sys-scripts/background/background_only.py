#!/usr/bin/env python3

import os
from time import sleep
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--dir", type=int, default=1, help="1/-1 direction to cycle through background")

idx_path = "/home/v18/.config/sys-scripts/background/next_idx.txt"

bg_path = "/home/v18/.config/sys-scripts/background/bg.txt"

script = "~/.config/sys-scripts/background/randbg.sh"


class Theme:

    def __init__(self, img: str, modules: str) -> None:
        self.img = img
        self.modules = modules

    def run(self):
        os.system(f"sh {script} {self.img}")
        sleep(1.5)
        # os.chdir("/home/v18/.config/style-change")
        # os.system(f"sh style-change.sh change {self.modules}")
    


def main():
    args = parser.parse_args()

    themes = (
            Theme("~/.config/Backgrounds/mnts2.png", "light-blue-waybar light-blue-neofetch light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/mntfuji.jpg", "forest-waybar forest-neofetch forest-zsh-color"),
            Theme("~/.config/Backgrounds/citycotton.jpeg", "light-blue-waybar light-blue-neofetch light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/flowers.png", "purple-waybar purple-neofetch light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/powerline.png", "orange-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/cityscape.jpg", "orange-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/saturn.png", "orange-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/summerbeach.jpg", "dark-orange-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/awawaaaaa.jpg", "dark-purple-waybar-bottom purple-neofetch light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/br49.png", "yellow-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/carinside.png", "orange-waybar orange-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/cityscape2.jpg", "light-blue-waybar light-blue-neofetch light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/flowersreal.jpg", "purple-waybar purple-neofetch"),
            Theme("~/.config/Backgrounds/mnts.jpg", "light-blue-waybar light-blue-neofetch"),
            Theme("~/.config/Backgrounds/carscity.jpg", "dark-purple-waybar-bottom purple-neofetch"),
            Theme("~/.config/Backgrounds/blue_sky.jpg", "light-light-blue-waybar light-light-blue-neofetch light-light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/sky_clouds.jpg", "light-light-blue-waybar light-light-blue-neofetch light-light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/ship_port.jpg", "light-light-blue-waybar light-light-blue-neofetch light-light-blue-zsh-color"),
            Theme("~/.config/Backgrounds/sky_green_hill.jpg", "forest-waybar forest-neofetch forest-zsh-color"),
            Theme("~/.config/Backgrounds/plane_terminal.jpg", "yellow-waybar yellow-neofetch orange-zsh-color"),
            Theme("~/.config/Backgrounds/chile_mnts.png", "blue-purple2-waybar blue-purple2-neofetch blue-purple2-hypr light-light-blue-zsh-color"),
            )
    


    f = open(f"{idx_path}", "r+")
    idx = str(f.read())
    f = open(f"{idx_path}", "w")
    f.write(str((int(idx)+args.dir) % len(themes)))
    f.close()
    
    theme = themes[(int(idx)+args.dir) % len(themes)]

    f = open(f"{bg_path}", "w")
    f.write(str(theme.img+"\n"))
    f.close()
    
    theme.run()


if __name__ == "__main__":
    main()

