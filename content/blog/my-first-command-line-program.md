---
title: "My first Command Line program"
slug: "my-first-command-line-program"
section: "programming-concepts"
datePublished: "2024-04-03T13:30:50.340Z"
description: "Discover how this Python command-line tool, developed as a CS50 final project, generates secure passwords with customizable lengths and character sets, ensu"
seoTitle: "Secure Password Generator: A Python CLI Tool for CS50 Final Project"
tags: ["python", "terminal", "cli", "password-generator", "cli-tool"]
cover: "img/my-first-command-line-program/c0db06a591d9.webp"
coverAlt: ""
hashnode: {"cuid": "clujuj1ic000f08lcbpdhe7c4", "url": "https://sukalyanroy.hashnode.dev/my-first-command-line-program"}
---

The following is an unedited glimpse into my notes and thoughts while I made my CS50 final project, a terminal application.

---

# Password Generator

---

What's this all about? Passwords. This tool uses the command line interface to help you create unique passwords based on a variety of options.

![](img/my-first-command-line-program/a0af73606c3e.webp)

Don't feel like remembering all these flags? Just do an interactive version instead!

![](img/my-first-command-line-program/02c4106f2e27.webp)

---

# Notes

This is where I'll make my first CLI program as the final project to CS50. Creating an entire project may seem daunting. Here are some questions that you should think about as you start:

* What will your software do? What features will it have? How will it be executed? It will be a password generator that works in two ways. Either it will ask the user a set of questions about the parameters or work directly with the flags provided in the terminal.
    
* What new skills will you need to acquire? What topics will you need to research? Complete CLI development is new to me. Along with that I have to learn about asynchronous code. Now I can work either with Javascript or Python and I haven't decided which one to use yet.
    
* In the world of software, most everything takes longer to implement than you expect. And so it’s not uncommon to accomplish less in a fixed amount of time than you hope. What might you consider to be a good outcome for your project? A better outcome? The best outcome? A good outcome would be a program that just works with the core functionality but doesn't have all the aesthetics or the flag options. better outcome would be colours and aesthetics. Best outcome would be a complete sets of flags and pipeline support.
    

[https://clig.dev/#the-basics](https://clig.dev/#the-basics)

The program will be a CLI application built using Python using the [click](https://click.palletsprojects.com/en/8.1.x/),[rich](https://github.com/Textualize/rich),[textual](https://github.com/Textualize/textual) libraries

Alternatively you could use Javascript using [Chalk](https://github.com/chalk/chalk),[inquirer](https://github.com/SBoudrias/Inquirer.js/)  
or using Rust\]using [clap](https://docs.rs/clap/latest/clap/).

Things to do

1. Make the program such that it can take input from multiple file formats and give output in multiple formats.
    
2. Make the program such that there is a detailed documentation built into it, much like a help command. **Display help text when passed no options, the**`-h` flag, or the `--help` flag. The concise help text should only include: A description of what your program does. One or two example invocations. Descriptions of flags, unless there are lots of them. An instruction to pass the `--help` flag for more information.
    
3. Make the program standalone so that the user does not have to worry about dependencies.
    
4. Think about all the possible errors and how to effectively show the error logs without saying too much or too little.
    
5. **Send messaging to**`stderr`. Log messages, errors, and so on should all be sent to `stderr`. This means that when commands are piped together, these messages are displayed to the user and not fed into the next command.
    

**Out of these, points 1 and 5 are incomplete as of now, I would like to get to them later someday.**

## General features

The only thing left is to test everything out point by point.

1. Questionnaire or flagged? IF there are no flags mentioned while calling the program in the command line, then it launches into a questionnaire, otherwise it leaves everything else the same and works based on the flags provided.
    
2. Password length: Question: "How long do you want the password to be?" Flag: `-l` and `--length`
    
3. Character Customization: Question: "Do you want to change which characters occur in the password?" IF they say yes then ask about each of Upper case, Lower case, Digits and Special characters. By default have all of them turned on. Flag: `-noUp`,`-noLow`,`-noDig` and `-noSpe` to disable each of the four types of characters.
    
4. Beginning with a particular character. Question: "Do you want the password to start with a particular type of character?" IF they say yes then do exactly as you did for point 2. Flag: `-begL`, `-begNum`,`-begSpe` for the password to begin with those respectively.
    
5. No similar characters: Question: "Do you want there to be similar characters like i, l, 1, L, o, 0, O?" If yes then ok else apply the logic to exclude similar characters. Flag: `-noSim`.
    
6. No duplicate characters: Question: "Do you want there to be duplicate Characters?" If yes then leave as is, if no then implement the logic for this. Flag: `-noDup`
    
7. No sequential Characters: Question: "Do you want to exclude sequential characters like abc or 789?" If no then leave it, if yes then apply the logic. Flag: `-noSeq`
    
8. Number of passwords to generate: Question: "How many passwords do you want to generate?" This value has to be a positive integer. Flag: `-genNum number`
    
9. Randomization algorithm. This one you should pick your own, it's not a user choice. Or should you put on here??? Question: "Do you want to provide your own seed for the randomization algorithm?" If no then use defaults else Add the feature for the user to provide a secure seed and change the algorithm based on that.
    
10. Hashing Passwords: Question: "Do you want your password to be hashed?" If yes then do a SHA-256 hash. Add more later flag: `-hash`
    

## Python approach

First display a banner using figlet, "Password generator". using [this](https://towardsdatascience.com/prettify-your-terminal-text-with-termcolor-and-pyfiglet-880de83fda6b) Then give the password if arguments are given else start the questionnare

We use the click module for parsing command line stuff and it works as follows: We first need to add `@click.command()` above our function to make sure it's working with it. Then we can add each flag using the `@click.option('flag', default='',help='This will be shown when the help command is run')`,where for example, `@click.option('--string', default='world')` is used to take a string input from user but has world as the default so we can just print hello world by default or hello name if we pass a name.

use `click.echo("statement")` instead of print function when using click. One problem i have noticed is that if you have a print function and an echo function both in one code, the type that comes first will only be executed. That is if print is used even once first, that will work but all the echos won't work. So the best practice would be to use echo or print consistently for everything.

We can also add sub-commands by defining a function within a click command and then writing the other commands as functionName.command()

For example:

```python

@click.group()
def cli():
    pass 

@cli.command()
@click.option('--name', default='world', help='Name of the person to greet.')
def greet(name):
    click.echo(colored(f.renderText('Password Generator'),'red'))
    click.echo('Hello there %s' %name)
    # print('Hello there %s' %name)
if __name__ == '__main__':

    cli()
```

Now to add the graphics using Textual and rich. Here I have to make a decision, whether to add simple colors using Rich or making a complete GUI like app within the terminal using textual.

Let's do the simpler one first then try out the complex one. Probably i'll use textual in a later more massive program. [https://www.youtube.com/playlist?list=PLHhDR\_Q5Me1MxO4LmfzMNNQyKfwa275Qe](https://www.youtube.com/playlist?list=PLHhDR_Q5Me1MxO4LmfzMNNQyKfwa275Qe)

Had to use UPX to compress the executable file size down from 64mb to 50mb but that's still not enough. Now im gonna try to setup a virtual environment.

Within the virtual environment it only decreases the size from 12mb to 11mb so not worth having the extra dependency.

To run this venv, after ive initialized it, i have to run the following command for Powershell to allow me to enter the venv `Set-ExecutionPolicy RemoteSigned` then `.\venv\Scripts\Activate`

Then install all the packages you need *including* pyinstaller. Because if you don't the global pyinstaller will work and inflate your application size.

The following is the executable making command that finally worked for me when turning the python code into a funcitoning executable.

```plaintext
  pyinstaller --onefile --upx-dir=C:\Users\Admin\Desktop\cli\upx-4.2.1-win64 -F --collect-all pyfiglet --strip .\password_generator.py
```

And everything Just works.

### Rich

I am using this to pretty print the tracebacks and add progress bars to my program.

### Final code in python  

This post was a minimally edited version so i am not going line by line through the code. One thing I have realized is that I used too many packages, so a future update might be to get the same functionality with fewer packages.

In making this, I almost gave up at many points when the code was not making sense and even chatgpt was not giving accurate solutions. But I persevered and in the end I fixed those problems myself. So this goes to prove that if AI cannot help in such small and simple projects, then it has a long way to go before reasonably replacing Software engineers.

```python
from termcolor import colored

from pyfiglet import Figlet

import click

import string

import time

import random

import hashlib

from rich.progress import track

from rich.traceback import install

install() # These two lines give us a pretty looking traceback

  

f = Figlet(font='standard')

  

@click.command()

@click.option('--name', default='user', help='Name of the person to greet.')

@click.option('-l', '--length', type=int,default = 5, help='Password length')

@click.option('-noUp', '--no_upper', is_flag=True, help='Exclude uppercase characters')

@click.option('-noLow', '--no_lower', is_flag=True, help='Exclude lowercase characters')

@click.option('-noDig', '--no_digits', is_flag=True, help='Exclude digits')

@click.option('-noSpe', '--no_special', is_flag=True, help='Exclude special characters')

@click.option('-begL', '--begin_letter', is_flag = True, help='Start with a specific letter')

@click.option('-begNum', '--begin_number',is_flag = True , help='Start with a specific number')

@click.option('-begSpe', '--begin_special',is_flag = True , help='Start with a specific special character')

@click.option('-noSim', '--no_similar', is_flag=True, help='Exclude similar characters (i, l, 1, L, o, 0, O)')

@click.option('-noDup', '--no_duplicates', is_flag=True, help='Exclude duplicate characters')

@click.option('-noSeq', '--no_sequential', is_flag=True, help='Exclude sequential characters')

@click.option('-genNum', '--num_passwords', type=int, default = 1, help='Number of passwords to generate')

@click.option('-hash', '--hash_password', is_flag=True, help='Hash the generated password using SHA-256')

@click.option('-seed', '--random_seed', type=int, default = 69420, help='Seed for the randomization algorithm')

@click.option('-f', '--file', type=click.File('w'), help='File to write the passwords to')

def start(name, length, no_upper, no_lower, no_digits, no_special, begin_letter,

          begin_number, begin_special, no_similar, no_duplicates, no_sequential,

          num_passwords, hash_password, random_seed,file):

       """

       This function greets the user and generates passwords.

       To use with flags, example:

       password.exe --name Suka --length 10 --begin_letter --no_similar --no_duplicates --no_sequential --num_passwords 2 --hash_password

       Will give the following output:

       the banner

       Hello there Suka

       Generated Password 1: }f'T*8;?pN (Hash: 7195d36954170f1d2bb23d3b77a2d9fc74ba18a9eb9643a6f8b57bac0cdab848)

       Generated Password 2: Jxn%(6H>W (Hash: 3dcc569eb36c1766b23e0a01775c40fcf31f1ea4185e20b0b08b1e8c99c0af29)

       """

       click.echo(colored(f.renderText('Password Generator'),'red'))

       click.echo(colored('Hello there %s' %name,'green'))

    # print('Hello there %s' %name)

       if not any([no_upper, no_lower, no_digits, no_special, begin_letter, begin_number,

                begin_special, no_similar, no_duplicates, no_sequential, hash_password,file]):

                    for i in track(range(100), description='Loading...'):

                        time.sleep(0.01) # This gives us a nice loading bar

                    click.echo(colored('Welcome to the Password Generator', 'blue'))

                    click.echo(colored('Please answer the following questions to generate your password', 'blue'))

                    length = click.prompt("How long do you want the password to be?", type=int)

                    no_upper = not click.confirm("Include uppercase characters?")

                    no_lower = not click.confirm("Include lowercase characters?")

                    no_digits = not click.confirm("Include digits?")

                    no_special = not click.confirm("Include special characters?")

                    no_similar = not click.confirm("Exclude similar characters (i, l, 1, L, o, 0, O)?")

                    no_duplicates = not click.confirm("Exclude duplicate characters?")

                    no_sequential = not click.confirm("Exclude sequential characters?")

                    if click.confirm("Do you want to start the password with a particular type of character?"):

                        # Ask for eac   h type individually

                        begin_letter = False

                        begin_number = False

                        begin_special = False

                        if click.confirm("Do you want to start with a letter?"):

                            begin_letter = True

                        elif click.confirm("Do you want to start with a number?"):

                            begin_number = True

                        else:

                            begin_special = True

                    num_passwords = click.prompt("How many passwords do you want to generate?", type=int, default=1, show_default=True)

                    if click.confirm("Do you want your password to be hashed?"):

                        hash_password = True

                        if click.confirm("Do you want to provide your own numeric seed for the randomization algorithm?", default = False):

                                random_seed = click.prompt("Enter your seed", type=int)

  

                        if random_seed:

                            random.seed(random_seed)

       passwords = [] # This will be an array of passwords

  

       for _ in range(num_passwords):

           password = generate_single_password(length, no_upper, no_lower, no_digits, no_special,

                                        begin_letter, begin_number, begin_special,

                                        no_similar, no_duplicates, no_sequential)

           passwords.append(password)

  

       for i, password in enumerate(passwords, start=1):

            if hash_password:

                hashed_password = hashlib.sha256(password.encode()).hexdigest()

                if file:

                    file.write(f'Generated Password {i}: {password} (Hash: {hashed_password})\n')

                click.echo(colored(f'Generated Password {i}: {password} (Hash: {hashed_password})', 'yellow'))

            else:

                if file:

                    file.write(f'Generated Password {i}: {password}\n')

                click.echo(colored(f'Generated Password {i}: {password}', 'blue'))

       if file:

           click.echo(colored('Your passwords have been saved to the file', 'green'))

           file.close()

def generate_single_password(length, no_upper, no_lower, no_digits, no_special,

                            begin_letter, begin_number, begin_special,

                            no_similar, no_duplicates, no_sequential):

    """This function generates a single password"""

    characters = ''

    if not no_upper:

        characters += string.ascii_uppercase

    if not no_lower:

        characters += string.ascii_lowercase

    if not no_digits:

        characters += string.digits

    if not no_special:

        characters += string.punctuation

  

    if no_similar:

        characters = characters.translate(str.maketrans('', '', 'il1Lo0O'))  # Exclude similar characters

  

    passwor = ''

    if begin_letter:

        passwor += random.choice(string.ascii_letters)

    elif begin_number:

        passwor += random.choice(string.digits)

    elif begin_special:

        passwor += random.choice(string.punctuation)

  

    passwor += ''.join(random.sample(characters, length - len(passwor)))

  
  
  

    if no_duplicates:

        passwor = ''.join(set(passwor))  # Remove duplicates

    if no_sequential:

        passwor = remove_sequential_characters(passwor)  # Remove sequential characters

  

    return ''.join(passwor)

  

def remove_sequential_characters(characters):

    # Remove sequential characters like abc or 789

    new_characters = ''

    for i, char in enumerate(characters):

        if i == 0 or characters[i - 1] != chr(ord(char) - 1):

            new_characters += char

    return new_characters

  

if __name__ == '__main__':

    start()
```

## Links

[https://github.com/Sukalyan2003/Password-Generator](https://github.com/Sukalyan2003/Password-Generator)