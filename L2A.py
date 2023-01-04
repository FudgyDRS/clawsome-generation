import json
import os
import ffmpeg
import random
import time
import boto3
import requests
import shutil

start = time.time()

staticDir = "C:/Users/CharlesTaylor/Documents/fudgylabs/clawsome_halloween/Cat Gif/LAYERS"
animDir = "C:/Users/CharlesTaylor/Documents/fudgylabs/clawsome_halloween/Cat Gif/Motion Layers"

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
  
staticAtt = generate_layers(staticDir)
animAtt = generate_layers(animDir)

print(json.dumps(staticAtt, indent=2))
print(json.dumps(animAtt, indent=2))

end = time.time()
print("Time elapsed: ", end - start)
