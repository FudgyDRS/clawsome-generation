import json
import os
import ffmpeg
import random
import time
import boto3
import requests
import shutil

start = time.time()
'''
create metadata files
needs elements:
  name
  description
  animation_url
  image
  external_link
  seller_fee_base_points
  fee_recipient
  edition
  date
  attributes
    trait_type  Background
    trait_type  Horse
    trait_type  Frame Background
    trait_type  Frame
    trait_type  Symbol
'''

def compress_video_noaudio(video_full_path, output_file_name, target_size):
    # Reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
    min_audio_bitrate = 32000
    max_audio_bitrate = 256000

    probe = ffmpeg.probe(video_full_path)
    # Video duration, in s.
    duration = float(probe['format']['duration'])
    # Target total bitrate, in bps.
    target_total_bitrate = (target_size * 1024 * 8) / (1.073741824 * duration)

    # Target video bitrate, in bps.
    video_bitrate = target_total_bitrate

    i = ffmpeg.input(video_full_path)
    ffmpeg.output(i, os.devnull,
      **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
      ).overwrite_output().run()
    ffmpeg.output(i, output_file_name,
      **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac'}
      ).overwrite_output().run()

def compress_video(video_full_path, output_file_name, target_size):
    # Reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
    min_audio_bitrate = 32000
    max_audio_bitrate = 256000

    probe = ffmpeg.probe(video_full_path)
    # Video duration, in s.
    duration = float(probe['format']['duration'])
    # Audio bitrate, in bps.
    audio_bitrate = float(next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])
    # Target total bitrate, in bps.
    target_total_bitrate = (target_size * 1024 * 8) / (1.073741824 * duration)

    # Target audio bitrate, in bps
    if 10 * audio_bitrate > target_total_bitrate:
        audio_bitrate = target_total_bitrate / 10
        if audio_bitrate < min_audio_bitrate < target_total_bitrate:
            audio_bitrate = min_audio_bitrate
        elif audio_bitrate > max_audio_bitrate:
            audio_bitrate = max_audio_bitrate
    # Target video bitrate, in bps.
    video_bitrate = target_total_bitrate - audio_bitrate

    i = ffmpeg.input(video_full_path)
    ffmpeg.output(i, os.devnull,
      **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
      ).overwrite_output().run()
    ffmpeg.output(i, output_file_name,
      **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac', 'b:a': audio_bitrate}
      ).overwrite_output().run()


'''
JSON layout:
{
  "name": "name",
  "description": "description",
  "animation_url": "animation_url",
  "image": "image_url",
  "external_link": "external_url",
  "seller_fee_base_points": "seller_fee_base_points",
  "fee_receipient": "fee_receipient",
  "edition": #
  "date": #
  "attributes": []
}
'''
def generate_metadata_base(
  name,
  description,
  external_link,
  seller_fee_base_points,
  fee_recipient,
  date
  ):
  metadata = json.loads("{}")
  metadata["name"] = "Horse+BG"
  metadata["description"] = description
  metadata["animation_url"] = "http://assets100.omnihorse.io/Horse+BG/&&&&.mp4"
  metadata["image"] = "http://assets100.omnihorse.io/Horse+BG/&&&&.gif"
  metadata["external_link"] = external_link
  metadata["seller_fee_base_points"] = seller_fee_base_points
  metadata["fee_receipient"] = fee_recipient
  metadata["edition"] = 1234567890
  metadata["date"] = date
  metadata["attributes"] = []
  return metadata


'''
JSON layout:
{
  "trait_type": [
    {
      "trait": "type",
      "values": [
        "value"
      ]
    }
  ]
}
'''
def generate_layers(directory):
  n=0
  attributes = json.loads("{}")
  attributes["trait_type"] = json.loads("[]")
  for layerDir in os.listdir(directory):
    attributes["trait_type"].append({"trait": layerDir, "values": []})
    for value in os.listdir(directory + "/" + layerDir):
    #from layer directory, create a JSON file of all layers and 
      attributes["trait_type"][n]["values"].append(value.split(".")[0])
    #print(json.dumps(attributes, indent=2))
    n += 1
  return attributes


'''
JSON layout:
{
  "name": "name",
  "description": "description",
  "animation_url": "animation_url",
  "image": "image_url",
  "external_link": "external_url",
  "seller_fee_base_points": "seller_fee_base_points",
  "fee_receipient": "fee_receipient",
  "edition": #
  "date": #
  "attributes": [
    { "trait_type": "type", "value": "value" }
  ]
}
'''
def generate_metadata(baseDirectory, baseMetadata, attributes, size):
  path = os.path.abspath(baseDirectory) + '/json'
  if not os.path.exists(path):
        os.makedirs(path)
  else:
    options = ['y', 'n']
    user_input = ""
    while user_input.lower() not in options:
      print('PATH: ', path, '\nDirectory \'json\' already exists, are you sure you want to delete it?')
      user_input = input('(y = yes, n = No):')
      if user_input.lower() == 'y':
        try:
          shutil.rmtree(path)
          os.makedirs(path)
        except OSError as e:
          print("Error: %s : %s" % (path, e.strerror))
      elif user_input.lower() == 'n':
        exit("User exited program")
      else:
        print('Type yes or no (y = yes, n = No):')

  i=0
  hashes = []
  while i < size:
    metadata = baseMetadata
    metadata = json.loads(json.dumps(baseMetadata)
      .replace('1234567890' , str(i))
      .replace('&&&&' , str(i)))
    #print(json.dumps(metadata, indent=2))
    
    
    #for j in range(0,size-1):
    flag = True
    while flag:
      values = []
      for trait in attributes["trait_type"]:
        length = len(trait["values"])
        #print("attributes length: ", length)
        value = trait["values"][random.randint(0,length-1)]
        #print("attribute value: ", value)
        values.append(value)
        metadata["attributes"].append({"trait_type": trait["trait"], "value": value})
      #metadata = json.loads(json.dumps(metadata)
      #  .replace('Horse+BG' , str(i)))
      newHash = str(hash(tuple(values)))
      if newHash in hashes:
        flag = True
      else:
        flag = False
        hashes.append(newHash)
    #print(json.dumps(metadata, indent=2))
    with open(path + '/' + str(i), 'w') as file:
      file.write(json.dumps(metadata, indent=2))
    i+=1

# './json/1.json'
def createArray(jsonFile):
  with open(jsonFile) as f:
    data = json.load(f)
    layers = data["attributes"]
    layersArray = [None] * 4
    for layer in layers:
      if layer["trait_type"] == "Background":
        layersArray[0] = layer["value"] + ".png"
      elif layer["trait_type"] == "Frame Background":
        layersArray[1] = layer["value"] + ".mov"
      elif layer["trait_type"] == "Frame":
        layersArray[2] = layer["value"] + ".mov"
      elif layer["trait_type"] == "Symbol":
        layersArray[3] = layer["value"] + ".mov"
    return layersArray

def generate_mp4(baseDirectory, inputDir):
  path = os.path.abspath(baseDirectory) + '/mp4'
  if not os.path.exists(path):
    os.makedirs(path)
  else:
    options = ['y', 'n']
    user_input = ""
    while user_input.lower() not in options:
      print('PATH: ', path, '\nDirectory \'mp4\' already exists, are you sure you want to delete it?')
      user_input = input('(y = yes, n = No):')
      if user_input.lower() == 'y':
        try:
          shutil.rmtree(path)
          os.makedirs(path)
        except OSError as e:
          print("Error: %s : %s" % (path, e.strerror))
      elif user_input.lower() == 'n':
        exit("User exited program")
      else:
        print('Type yes or no (y = yes, n = No):')

  for filename in os.listdir(inputDir):
    if filename != "_metadata.json":
      layers = createArray(os.path.abspath(inputDir) + '/' + filename)
      #print(layers)
      #print("Generating MOV output: ")
      layer5 = ffmpeg.input(os.path.abspath(baseDirectory) + '/layers/Background/' + layers[0])
      layer4 = ffmpeg.input(os.path.abspath(baseDirectory) + '/layers/Horse/Horse+BG.mov')
      layer3 = ffmpeg.input(os.path.abspath(baseDirectory) + '/layers/Frame Background/' + layers[1])
      layer2 = ffmpeg.input(os.path.abspath(baseDirectory) + '/layers/Frame/' + layers[2])
      layer1 = ffmpeg.input(os.path.abspath(baseDirectory) + '/layers/Symbol/' + layers[3])
      (
        layer5
        .overlay(layer4)
        .overlay(layer3)
        .overlay(layer2)
        .overlay(layer1)
        .output(path + '/' + filename + '.mp4')
        .run()
      )

def generate_gif(baseDirectory):
  path = os.path.abspath(baseDirectory) + '/gif'
  if not os.path.exists(path):
    os.makedirs(path)
  else:
    options = ['y', 'n']
    user_input = ""
    while user_input.lower() not in options:
      print('PATH: ', path, '\nDirectory \'gif\' already exists, are you sure you want to delete it?')
      user_input = input('(y = yes, n = No):')
      if user_input.lower() == 'y':
        try:
          shutil.rmtree(path)
          os.makedirs(path)
        except OSError as e:
          print("Error: %s : %s" % (path, e.strerror))
      elif user_input.lower() == 'n':
        exit("User exited program")
      else:
        print('Type yes or no (y = yes, n = No):')

  inPath = os.path.abspath(baseDirectory) + '/mp4'
  for filename in os.listdir(inPath):
    layer = ffmpeg.input(inPath + '/' + filename)
    size = len(filename)
    print("file for ffmpeg: ", baseDirectory + '/mp4/' + filename)
    (
      layer
      .overlay(layer).filter('scale', 350, -1)
      .output(path + '/' + filename[:size - 3] + 'gif')
      .run()
    )

# =============================================================================
#================================SETUP OF SCRIPT===============================
# =============================================================================


# =============================================================================
#================================START OF SCRIPT===============================
# =============================================================================
if not os.path.exists('config.json'):
  print('PATH: ', os.path.abspath('config.json'))
  exit('ERROR: config.json is missing')

with open(os.path.abspath('config.json'), 'r') as file:
  filedata = json.loads(file.read())
  Accessory   = filedata["nft_settings"]["Accessory"]
  Hat         = filedata["nft_settings"]["Hat"]
  Glasses     = filedata["nft_settings"]["Glasses"]
  Hair        = filedata["nft_settings"]["Hair"]
  Eyes        = filedata["nft_settings"]["Eyes"]
  Clothing    = filedata["nft_settings"]["Clothing"]
  Cat         = filedata["nft_settings"]["Cat"]

  Glasses_SP  = filedata["special"] #logic for 
  base_metadata = filedata["base_metadata"]
  total_supply = filedata["total_supply"]

if not os.path.exists('cat_names.json'):
  print('PATH: ', os.path.abspath('cat_names.json'))
  exit('ERROR: cat_names.json is missing')

with open(os.path.abspath('config.json'), 'r') as file:
  filedata = json.loads(file.read())
  Cat_Names  = filedata

def generate_metadata(baseDirectory, baseMetadata, size):
  path = os.path.abspath(baseDirectory) + '/json'
  if not os.path.exists(path):
        os.makedirs(path)
  else:
    options = ['y', 'n']
    user_input = ""
    while user_input.lower() not in options:
      print('PATH: ', path, '\nDirectory \'json\' already exists, are you sure you want to delete it?')
      user_input = input('(y = yes, n = No):')
      if user_input.lower() == 'y':
        try:
          shutil.rmtree(path)
          os.makedirs(path)
        except OSError as e:
          print("Error: %s : %s" % (path, e.strerror))
      elif user_input.lower() == 'n':
        exit("User exited program")
      else:
        print('Type yes or no (y = yes, n = No):')

  i = 0
  dna_list = []
  metadata = baseMetadata
  while i < size:
    flag = True
    while flag:
      metadata["attributes"] = json.loads("[]")
      dna = 0x0
      __type__ = "Accessory"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((dna << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Hat"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Glasses"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Hair"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Eyes"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Clothing"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Cat"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      __type__ = "Background"
      __array__ = filedata["nft_settings"][__type__]
      index = random.randint(0,len(__array__)-1)
      dna = hex((int(dna, 16) << 8) | int(__array__[index]["hex"], 16))
      metadata["attributes"].append({"trait_type": __type__, "value": __array__[index]["name"]})

      if metadata["attributes"][6]["value"] == "Spotted" and metadata["attributes"][3]["value"] == "Long":
        flag = True
      elif metadata["attributes"][2]["value"] == "Pineapple Shades" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Monocle" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Ladder Shades" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Reading Glasses" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Round Glasses" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Round Shades" and metadata["attributes"][4]["value"] == "Love to Death" or\
        metadata["attributes"][2]["value"] == "Round Shades" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][2]["value"] == "Butterfly Shades" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][2]["value"] == "Flame Shades" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][2]["value"] == "Fishy" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][2]["value"] == "Fishy" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][2]["value"] == "Fishy" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][2]["value"] == "None" and metadata["attributes"][4]["value"] == "None" or\
        metadata["attributes"][2]["value"] != "None" and metadata["attributes"][4]["value"] == "None" or\
        metadata["attributes"][2]["value"] != "None" and metadata["attributes"][4]["value"] == "Crying" or\
        metadata["attributes"][0]["value"] != "None" and metadata["attributes"][1]["value"] == "Royal Crown" or\
        metadata["attributes"][0]["value"] != "None" and metadata["attributes"][1]["value"] == "Headdress" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Right)" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Headphones" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][0]["value"] == "Earring Gold (Double)" and metadata["attributes"][1]["value"] == "Viking" or\
        metadata["attributes"][0]["value"] == "Earring Silver (Right)" and metadata["attributes"][1]["value"] == "Viking" or\
        metadata["attributes"][0]["value"] == "Earring Silver (Right)" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Jester Cap" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Tarboosh" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Crown" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Propeller Cap" or\
        metadata["attributes"][3]["value"] == "Bun" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Jester Cap" or\
        metadata["attributes"][3]["value"] == "Crazy Black" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Jester Cap" or\
        metadata["attributes"][3]["value"] == "Crazy Brown" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Tarboosh" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Viking" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Jester Cap" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Viking" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][3]["value"] == "Jester" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Propeller Cap" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Afro" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Headdress" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Propeller Cap" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Troll" and metadata["attributes"][1]["value"] == "Crown" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Tarboosh" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Viking" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Crown" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Propeller Cap" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][3]["value"] == "Bowl Cut" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Tophat" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Chef Hat" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Jester Cap" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Detective Cap" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Tarboosh" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Propeller Cap" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Sombrero" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Rocker" and metadata["attributes"][1]["value"] == "Hardhat" or\
        metadata["attributes"][3]["value"] == "Sauve" and metadata["attributes"][1]["value"] == "Fishy" or\
        metadata["attributes"][3]["value"] == "Sauve" and metadata["attributes"][1]["value"] == "Birthday Hat" or\
        metadata["attributes"][3]["value"] == "Sauve" and metadata["attributes"][1]["value"] == "Witch Hat" or\
        metadata["attributes"][3]["value"] == "Long" and metadata["attributes"][1]["value"] == "Pom Pom Blue" or\
        metadata["attributes"][3]["value"] == "Long" and metadata["attributes"][1]["value"] == "Pom Pom Brown" or\
        metadata["attributes"][3]["value"] == "Long" and metadata["attributes"][1]["value"] == "Pom Pom Red" or\
        metadata["attributes"][3]["value"] == "Long" and metadata["attributes"][1]["value"] == "Witch Hat":
        flag = True
      elif dna in dna_list:
        flag = True
      else:
        flag = False
        dna_list.append(dna)
        metadata["DNA"] = str(dna)

    
    with open(path + '/' + str(i), 'w') as file:
      file.write(json.dumps(metadata, indent=2))
    i+=1
    print(json.dumps(metadata, indent=2))

def createArray(jsonFile):
  with open(jsonFile) as f:
    data = json.load(f)
    layers = data["attributes"]
    layersArray = [None] * 7
    isMovie = False
    for layer in layers:
      print("I killed it2!")
      print(layer)
      if layer["trait_type"] == "Glasses" and layer["value"] == "Pineapple Shades":
        layersArray = [None] * 7
        for layer in layers:
          #########################################
          # Background
          #########################################
          if layer["trait_type"] == "Background":
            if layer["value"] == "Disco":
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Cat
          #########################################
          if layer["trait_type"] == "Cat":
            if (layer["value"] == "Ginger") or\
              (layer["value"] == "Oreo") or\
              (layer["value"] == "Psychedelic"):
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Clothing
          #########################################
          if layer["trait_type"] == "Clothing":
            layersArray[2] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Hair
          #########################################
          if layer["trait_type"] == "Hair":
            layersArray[3] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Glasses + Eyes
          #########################################
          if layer["trait_type"] == "Eyes":
            eyes = layer["value"]
            if eyes == "Angry Blue" or eyes == "Angry Green":
              eyes = "Angry"
            if eyes == "Cute Blue" or eyes == "Cute Green":
              eyes = "Cute"
            layersArray[4] = "layers/Glasses/" + "Pineapple Shades (" + eyes + ").png"
          #########################################
          # Hat
          #########################################
          if layer["trait_type"] == "Hat":
            layersArray[5] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Accessory
          #########################################
          if layer["trait_type"] == "Accessory":
            layersArray[6] ="layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
        break
      elif (layer["trait_type"] == "Glasses" and layer["value"] == "Reading Glasses") or\
           (layer["trait_type"] == "Glasses" and layer["value"] == "Round Glasses"):
        layersArray = [None] * 7
        glasses = layer["value"]
        for layer in layers:
          #########################################
          # Background
          #########################################
          if layer["trait_type"] == "Background":
            if layer["value"] == "Disco":
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Cat
          #########################################
          if layer["trait_type"] == "Cat":
            if (layer["value"] == "Ginger") or\
              (layer["value"] == "Oreo") or\
              (layer["value"] == "Psychedelic"):
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Clothing
          #########################################
          if layer["trait_type"] == "Clothing":
            layersArray[2] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Hair
          #########################################
          if layer["trait_type"] == "Hair":
            layersArray[3] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Glasses + Eyes
          #########################################
          if layer["trait_type"] == "Eyes":
            eyes = layer["value"]
            if eyes == "Angry Blue" or eyes == "Angry Green":
              eyes = "Angry"
            if eyes == "Cute Blue" or eyes == "Cute Green":
              eyes = "Cute"
            layersArray[4] = "layers/Glasses/" + glasses + " (" + eyes + ").png"
          #########################################
          # Hat
          #########################################
          if layer["trait_type"] == "Hat":
            layersArray[5] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Accessory
          #########################################
          if layer["trait_type"] == "Accessory":
            layersArray[6] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
        break
      elif (layer["trait_type"] == "Glasses" and layer["value"] == "Monocle") or\
           (layer["trait_type"] == "Glasses" and layer["value"] == "Monocle"):
        layersArray = [None] * 7
        glasses = layer["value"]
        for layer in layers:
          #########################################
          # Background
          #########################################
          if layer["trait_type"] == "Background":
            if layer["value"] == "Disco":
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Cat
          #########################################
          if layer["trait_type"] == "Cat":
            if (layer["value"] == "Ginger") or\
              (layer["value"] == "Oreo") or\
              (layer["value"] == "Psychedelic"):
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Clothing
          #########################################
          if layer["trait_type"] == "Clothing":
            layersArray[2] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Hair
          #########################################
          if layer["trait_type"] == "Hair":
            layersArray[3] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Glasses + Eyes
          #########################################
          if layer["trait_type"] == "Eyes":
            eyes = layer["value"]
            layersArray[4] = "layers/Glasses/" + glasses + " (" + eyes + ").png"
          #########################################
          # Hat
          #########################################
          if layer["trait_type"] == "Hat":
            layersArray[5] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Accessory
          #########################################
          if layer["trait_type"] == "Accessory":
            layersArray[6] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
        break
      elif layer["trait_type"] == "Glasses" and layer["value"] != "None" and layer["value"] != "Ladder Shades":
        layersArray = [None] * 7
        for layer in layers:
          #########################################
          # Background
          #########################################
          if layer["trait_type"] == "Background":
            if layer["value"] == "Disco":
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Cat
          #########################################
          if layer["trait_type"] == "Cat":
            if (layer["value"] == "Ginger") or\
                (layer["value"] == "Oreo") or\
                (layer["value"] == "Psychedelic"):
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Clothing
          #########################################
          if layer["trait_type"] == "Clothing":
            layersArray[2] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Hair
          #########################################
          if layer["trait_type"] == "Hair":
            layersArray[3] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Glasses + Eyes
          #########################################
          if layer["trait_type"] == "Glasses":
            if layer["value"] == "Butterfly Shades":
              layersArray[4] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
              isMovie = True
            else:
              layersArray[4] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Hat
          #########################################
          if layer["trait_type"] == "Hat":
            layersArray[5] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
          #########################################
          # Accessory
          #########################################
          if layer["trait_type"] == "Accessory":
            layersArray[6] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
        break
      # Generic - if glasses is !none -> eyes
      #########################################
      # Background
      #########################################
      if layer["trait_type"] == "Background":
        if layer["value"] == "Disco":
          layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
          isMovie = True
        else:
          layersArray[0] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Cat
      #########################################
      if layer["trait_type"] == "Cat":
        if (layer["value"] == "Ginger") or\
            (layer["value"] == "Oreo") or\
            (layer["value"] == "Psychedelic"):
          layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
          isMovie = True
        else:
          layersArray[1] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Clothing
      #########################################
      if layer["trait_type"] == "Clothing":
        layersArray[2] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Hair
      #########################################
      if layer["trait_type"] == "Hair":
        layersArray[3] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Glasses + Eyes
      #########################################
      if layer["trait_type"] == "Eyes":
          if layer["value"] == "Love to Death":
            layersArray[4] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".mov"
            isMovie = True
          else:
            layersArray[4] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Hat
      #########################################
      if layer["trait_type"] == "Hat":
        layersArray[5] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"
      #########################################
      # Accessory
      #########################################
      if layer["trait_type"] == "Accessory":
        layersArray[6] = "layers/" + layer["trait_type"] + "/" + layer["value"] + ".png"

    if layersArray[3].split(".")[0] == "Sauve":
      temp = layersArray[4]
      layersArray[4] = layersArray[3]
      layersArray[3] = temp
    finalArray = []
    print("layersarray: ", layersArray)
    for layer in layersArray:
      if "None.png" not in layer:
        finalArray.append(layer)
    return finalArray, isMovie

def generate_mp4(baseDirectory, inputDir):
  path = os.path.abspath(baseDirectory) + '/mp4'
  if not os.path.exists(path):
    os.makedirs(path)
  else:
    options = ['y', 'n']
    user_input = ""
    while user_input.lower() not in options:
      print('PATH: ', path, '\nDirectory \'mp4\' already exists, are you sure you want to delete it?')
      user_input = input('(y = yes, n = No):')
      if user_input.lower() == 'y':
        try:
          shutil.rmtree(path)
          os.makedirs(path)
        except OSError as e:
          print("Error: %s : %s" % (path, e.strerror))
      elif user_input.lower() == 'n':
        exit("User exited program")
      else:
        print('Type yes or no (y = yes, n = No):')

  for filename in os.listdir(inputDir):
    layers, isMovie = createArray(os.path.abspath(inputDir) + '/' + filename)
    #print(layers)
    #print("Generating MOV output: ")
    print("processing: ", layers)
    length = len(layers)
    video = ''
    i=0
    for layer in layers:
      print("layer: ", layer)
      if i==0:
        video = ffmpeg.input(os.path.abspath(baseDirectory) + '/' + layer)
      video = video.overlay(ffmpeg.input(os.path.abspath(baseDirectory) + '/' + layer))
      i += 1
    
    #something = ffmpeg.input("/layer1/3.png")
    #something2 = ffmpeg.input("/layer1/3.png")
    #print("something3", (something.overlay(something2)).output("/newfilepath/4" + '.mp4'))
#
    #print("something", something)
    #print("something2", something2)
    ##print("something3", something3)
    #video = layersArray[0]
    #while(j<i):
    #  j += j
    #  video.overlay(layersArray[j])
    (
        video
        .output(path + '/' + filename + ('.mp4' if isMovie else '.png'))
        .run()
    )
try:
  int(total_supply)
except:
  print('total_supply:', total_supply)
  exit('Error: total_supply bad value in config.json')
#thing = json.dumps(base_metadata, indent=2)
print(json.dumps(base_metadata, indent=2))
generate_metadata(".", base_metadata, total_supply)
generate_mp4(".", "./json")
'''
Foreground
Accessory
Hat
Glasses
Hair
Eyes
Clothing
Cat
Background
01 23 45 67 89 01 23
'''



















'''



print("Welcome to Omnihorse horse generation: ")
print("Base metadata: ")
print(json.dumps(metadata, indent=2))
print(''.ljust(80, '='))
print('Layers directory structured correctly.')
print(''.ljust(80, '='))
input('Press Enter to generate Metadata files')
print(''.ljust(80, '='))

  
attributes = generate_layers(os.path.abspath(basedirectory) + '/layers')
print(''.ljust(80, '='))
generate_metadata(basedirectory, metadata, attributes, total_supply)
print(''.ljust(80, '='))
print('Metadata has been generated.')
input('Press Enter to generate MP4 and GIF files')
print(''.ljust(80, '='))
generate_mp4(basedirectory, os.path.abspath(basedirectory) + '/json')
print(''.ljust(80, '='))
print('MP4 files have been generated.')
generate_gif(basedirectory)
print(''.ljust(80, '='))
print('GIF files have been generated.')

for filename in os.listdir(os.path.abspath(basedirectory) + '/json/'):
  with open(os.path.abspath(basedirectory) + '/json/' + filename, 'r') as file:
    filedata = file.read()

  # Replace the Horse+BG with actual name
  filedata = filedata.replace('Horse+BG', horse_name)
  path = os.path.abspath(basedirectory) + '/json'
  if not os.path.exists(path):
    exit('ERROR: path ' + path + ' does not exist')
  with open(path + '/' + filename, 'w') as file:
    file.write(filedata)

# Generations complete, now to upload to AWS bucket
os.system('cls' if os.name == 'nt' else 'clear')
print('MP4 and GIF file generations complete, files are ready for upload')
print('Please take time to check if your images look correct:')
input('Press Enter to continue...')

print(''.ljust(80, '='))
print('AWS Bucket settings: ')
print('service_name ='.ljust(25, ' '), service_name)
print('region_name ='.ljust(25, ' '), region_name)
print('aws_access_key_id ='.ljust(25, ' '), aws_access_key_id)
print('aws_secret_access_key ='.ljust(25, ' '), aws_secret_access_key)
print('Bucket Name ='.ljust(25, ' '), bucket_name)

uploadSize = 0
countMP4 = 0
totalMP4Size = 0
uploadedMP4Size = 0
countGIF = 0
totalGIFSize = 0
uploadedGIFSize = 0
for path, dirs, files in os.walk(os.path.abspath(basedirectory) + '/mp4/'):
  countMP4 = len(files)
  for f in files:
    fp = os.path.join(path, f)
    uploadSize += os.path.getsize(fp)
    totalMP4Size += os.path.getsize(fp)
for path, dirs, files in os.walk(os.path.abspath(basedirectory) + '/gif/'):
  countGIF = len(files)
  for f in files:
    fp = os.path.join(path, f)
    uploadSize += os.path.getsize(fp)
    totalGIFSize += os.path.getsize(fp)

print(''.ljust(80, '='))
print('Number of MP4s: ', countMP4)
print('Total size of MP4s to be uploaded: ', "{:.4f}".format(totalMP4Size / 1024 / 1024), 'MB')
print('Number of GIFs: ', countGIF)
print('Total size of GIFs to be uploaded: ', "{:.4f}".format(totalGIFSize / 1024 / 1024), 'MB')
print('Total upload size: ', "{:.4f}".format(uploadSize / 1024 / 1024), 'MB')
print(''.ljust(80, '='))
input('Upload may take awhile, press Enter to continue...')

# Begin uploading MP4 files
count = 0
print('Uploading MP4 files: ')
for path, dirs, files in os.walk(os.path.abspath(basedirectory) + '/mp4/'):
  for f in files:
    count += 1
    fp = os.path.join(path, f)
    np = horse_name + '/' + f
    
    s3.Bucket(bucket_name).upload_file(Filename=os.path.abspath(fp), Key=np)
    uploadedMP4Size += os.path.getsize(fp)
    print('Uploading file: ', fp)
    print(count, 'of', countMP4, 'files uploaded\n'
    + str("{:.4f}".format(uploadedMP4Size / 1024 / 1024)), '/', str("{:.4f}".format(totalMP4Size / 1024 / 1024)), 'MB', end="\r")
    r = requests.head('http://' + bucket_name + '/' + np)
    if not r.status_code == requests.codes.ok:
      print('ERROR: file', f, 'failed to upload\n', 'STATUS:', r.status_code)
      options = ['y', 'n']
      user_input = ""
      while user_input.lower() not in options:
        print('Skip this error and continue the program?')
        user_input = input('(y = yes, n = No):')
        if user_input.lower() == 'y':
          input("Press Enter to continue the program...")
        elif user_input.lower() == 'n':
          exit("User exited program")
        else:
          print('Type yes or no (y = yes, n = No):')

print('\nMP4 files uploads complete!')
print(''.ljust(80, '='))
# Begin uploading MP4 files
count = 0
print('Uploading GIF files: ')
for path, dirs, files in os.walk(os.path.abspath(basedirectory) + '/gif'):
  for f in files:
    count += 1
    fp = os.path.join(path, f)
    np = horse_name + '/' + f
    
    s3.Bucket(bucket_name).upload_file(Filename=os.path.abspath(fp), Key=np)
    uploadedGIFSize += os.path.getsize(fp)
    print('Uploading file: ', fp)
    print(count, 'of', countGIF, 'files uploaded\n'
    + str("{:.4f}".format(uploadedGIFSize / 1024 / 1024)), '/', str("{:.4f}".format(totalGIFSize / 1024 / 1024)), 'MB', end="\r")
    r = requests.head('http://' + bucket_name + '/' + np)
    if not r.status_code == requests.codes.ok:
      print('ERROR: file', f, 'failed to upload\n', 'STATUS:', r.status_code)
      options = ['y', 'n']
      user_input = ''
      while user_input.lower() not in options:
        print('Skip this error and continue the program?')
        user_input = input('(y = yes, n = No):')
        if user_input.lower() == 'y':
          input('Press Enter to continue the program...')
        elif user_input.lower() == 'n':
          exit('User exited program')
        else:
          print('Type yes or no (y = yes, n = No):')

print('\GIF files uploads complete!')
print(''.ljust(80, '='))
print('Finalizing JSON metadata files, please wait a moment...')
for filename in os.listdir(os.path.abspath(basedirectory) + '/json'):
  with open(os.path.abspath(basedirectory) + '/json/' + filename, 'r') as file:
    filedata = json.loads(file.read())
    filedata['attributes'].pop(3)
    filedata['attributes'].append({"trait_type": "Level", "value": "Lv1"})
  with open(os.path.abspath(basedirectory) + '/json/' + filename, 'w') as file:
    file.write(json.dumps(filedata, indent=2))

print(''.ljust(80, '='))
print('End of program!')
"""
change json files to use
change to have option to use config file
create receipt log for the development team

"""
end = time.time()
print("Time elapsed: ", end - start)


'''
