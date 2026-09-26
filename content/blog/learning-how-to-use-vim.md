---
title: "Learning how to use Vim"
slug: "learning-how-to-use-vim"
section: "linux"
datePublished: "2024-02-28T06:38:17.390Z"
description: "Look at the basics of what vim is all about and have this handy cheatsheet to get you started"
seoTitle: "Vim basics and Cheatsheet"
tags: ["terminal", "vim"]
cover: "img/learning-how-to-use-vim/a391ef83c91e.webp"
coverAlt: ""
ogImage: "img/learning-how-to-use-vim/1ad89fa0dd7f.webp"
hashnode: {"cuid": "clt5fdooe00030al2br59gryp", "url": "https://sukalyanroy.hashnode.dev/learning-how-to-use-vim"}
---

So i've dabbled in Linux for a little bit over the years, never really committing to it, but I've always been fascinated by the Command Line interface.

To use certain linux tools in windows I used the Git Bash installation of Git in my Desktop PC, which adds a lot of the core terminal features to any OS, which in my case is Windows 10. (Though I have used the same in Windows 7 before as well).

One of those tools is the one called Vim.

![](img/learning-how-to-use-vim/729745d7d101.webp)

Vim, or Vi improved is the standard text editing solution for Linux terminal users, the Vim vs Emacs Debate aside. (Nano crying in the corner).

![](img/learning-how-to-use-vim/04dd8a9c6397.webp)

It has a very bare-bones interface for the untrained eyes, but with a closer look you can see the near infinite possibilities that the different commands, plugins and inbuilt features bring.

Now the picture above has some modifications from the default, which I will discuss later when talking about the .vimrc file, stay tuned.

There are many different features of Vim, but me being a basic user, do not know or use most of those. This post will deal with the basics and if demand is there for more, I will learn and talk about the different advanced features present in Vim.

## Basics

Let's deal with the basic controls first,  
When you enter Vim, you see that welcome message and you are in what is called the Normal mode or the Command mode.

Here you can move around the text using the keys h,j,k,l.  
`k` moves cursor up `j` moves it down. `l` moves it right and `h` moves it left.

<mark>A tip if you want to remember the key places, the </mark> `j` <mark> key in most keyboards has a little bit of material poking out, similarly with the </mark> `f` <mark> key. This can be used to find your way back in the key positions.</mark>

But if you want to edit the text, you have to enter **Insert mode** .  
`i` to enter insert mode and `esc` to exit it.`o` puts you one line below the cursor and `O` puts above the cursor; and into Insert mode.

You could also press \`I\` to insert at the beginning of the line.

And a to insert (append) after the cursor,

A - insert (append) at the end of the line.

Type whatever you want in the insert mode then exit it.

![](img/learning-how-to-use-vim/6bf1c48d6606.webp)

There is also a way to use the Vim inbuilt command line. For that press `esc` ro return to the Command mode, then press `:` followed by the command.

For example, You could also make multiple windows in Vim by using the command `:split` to do a horizontal split or `:vsplit` to do a vertical split.

![](img/learning-how-to-use-vim/1d69e3d267dd.webp)

**To move between windows, use**`Ctrl w` then normal movement commands like `k, l,j, h` etc to move.

<mark>And you can close the window by using </mark> `:q`<mark>. This works for any and all windows.</mark>

`w`**for saving changes and**`q`**for quitting. combine these two as**`:wq`**to write and quit.**`q!`**is to quit without saving.**

For a large text file, you would want some faster ways of navigating, for that you have the following:

Any number written before the a command repeats that command that number of times. For eg: `50k` moves you up by 50 lines.

And also, `gg` takes you to the top of a file and `G` takes you to the bottom.

For quick deleting, `dd` deletes the entire line(when in command mode). `D` deletes everything in the line which is to the right of the cursor.

`u` to undo an action. `Ctrl R` is redo.

Now those are some basics that you'd need, and preferably you will remember these basic things.

## Customization

All installations have a file called `.vimrc` that deals with customization, let's open it.

You open a file with vim, using `vim filename`.

![](img/learning-how-to-use-vim/8c6444eee9a7.webp)

The vimrc is located at the home directory denoted by `~`.

The following is my Vimrc, let's go through it line by line

![](img/learning-how-to-use-vim/48f7e377afb8.webp)

The first few lines deal with the file naming, line numbering, colour theme and extension management.

The important ones are the `syntax on` and the `set relativenumber` to enable the syntax features of vim and the line numbers respectively.

Then there is the Plugin sections, here I have used the [Vim Plug](https://github.com/junegunn/vim-plug) plugin manager to install plugins.

Once you add the needed lines in your vimrc, you need to run `:PlugInstall` and the rest will be handled by the plugin Manager.  
Check the common ones out for yourself and install as needed.

The status Line part is something I had copied from a site i cannot remember, which adds the weird little things in the status bar, giving more information about vim and the files it has opened.

There is also the topic of Vimscript and programming, deciding which plugins to install and other advanced navigation features of vim that I myself haven't completed learned yet.

One popular alternative to vim is Neovim, which adds Language Server protocol support to vim for massively better language specific tools. It also uses the much more popular language Lua for scripting rather than the obscure Vimscript.

Since Vim for me has been a way to keep being connected to the terminal, I have not tried Neovim yet. But I'll surely try it out someday.

## Cheatsheet

For extended use, there are a few more things, for which i'm listing the short cheatsheet I made for just the basics. There are much more comprehensive cheatsheets out there, but which I believe can be overwhelming for most newbies.

You can use the following when you need it but i would recommend reading some more tutorials and examples out there and use them to make your own cheatsheet as you go on.

Another important resource is the `vimtutor` command on the terminal that launches an interactive tutorial to teach all the basics of Vim. Do check it out.

Here's my short cheatsheet:

1. `k` moves cursor up `j` moves it down. `l` moves it right and `h` moves it left.
    
2. Any number written before the a command repeats that command that number of times. For eg: `50k` moves you up by 50 lines.
    
3. `i` to enter insert mode and `esc` to exit it.`o` puts you one line below the cursor and `O` puts above the cursor; and into Insert mode.
    
4. **To move between windows, use**`Ctrl w` then normal movement commands like `k, l,j, h` etc to move.
    
5. `:n` takes you to next file in argument, `:N` takes to previous. For when you have several files in argument, try `:bn` where `n` is the number of files you want to move forward. This loops back to the first one after passing over the last. `:bp` is to go to the previous one.
    
6. `w` for saving changes and `q` for quitting. combine these two to write and quit. `q!` is to quit without saving.
    
7. `dd` deletes the entire line(when in command mode). `D` deletes everything in the line which is to the right of the cursor.
    
8. `gg` takes you to the top of a file and `G` takes you to the bottom.
    
9. `{` and `}` are used to move up and down blocks of code.
    
10. `u` to undo an action. `Ctrl R` is redo.
    
11. `y` to "yank" or copy something. `yy` to copy a whole line. `p` to paste below the cursor and `P` to paste above the cursor.
    
12. `Shift V` enters visual mode where you can select and highlight blocks of text
    
13. `:"number"` takes you to that line.
    
14. `w` and `b` is used to move forward and backword one word at a time. `W` and `B` does the same but ignores punctuation(ie it skips to the next space). `0` takes you to the beginning of a line.
    
15. `t"character"` takes you to the position just before the character and `f` takes you to the character itself. You can mix this with other commands. For eg: `dt/` deletes everything untill the next `/` occurence.
    
16. `%` when used after a command applies that command to all the stuff in that block. For eg `B%` takes you to the end of a parenthesis if used on a starting parenthesis. similarly `d%` deletes everything in that parenthesis.
    
17. `C` is used to change a particular block of text. It deletes that block and puts you in insert mode.
    
18. `r` is used to replace letters. You can use numbers to repeat it.
    
19. `*` is used to toggle between the different instances of a word. `;` to go to the next instance.
    
20. `~` swaps the cases of letters.
    
21. `.` repeats the last command. For eg: if you used `dd` to delete a line, unless you use any other command inbetween, now you can delete a line using `.` any number of times you want.
    
22. `<` and `>` used to indent a block of text left or right respectively.
    
23. Macros: start recording your keystrokes with `q"macroname"` and replay them using `@macroname`.
    

## See you soon

This was my first technical blog on Hashnode and I do plan on writing more based on the few sets of notes I've taken in the past regarding different topics.

Do tell me if there is anything you want me to delve deeper into and I will try my best to write about it.

Some more resources:

[https://linuxhandbook.com/vim/](https://linuxhandbook.com/vim/)  
[https://github.com/junegunn/vim-plug](https://github.com/junegunn/vim-plug)