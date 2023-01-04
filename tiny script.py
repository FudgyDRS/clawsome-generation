import json
import os
import time
import shutil

start = time.time()
path = './truth_json'
if not os.path.exists(path):
  os.makedirs(path)
else:
  options = ['y', 'n']
  user_input = ""
  while user_input.lower() not in options:
    print('PATH: ', path, '\nDirectory \'truth_json\' already exists, are you sure you want to delete it?')
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

for i in range(0, 949):
  metadata = json.loads("{}")
  metadata["name"] = "Truth Seekers Presale NFT #" + str(i) 
  metadata["description"] = "TruthSeeker NFT give customer access to the TRUTH ecosystem and potential revenue share. Truth Seekers is the Next Generation Of Crypto Security Firms."
  metadata["image"] = "https://ibb.co/Yb6FX7F"
  metadata["edition"] = i
  with open(path + '/' + str(i) + ".json", 'w') as file:
    file.write(json.dumps(metadata, indent=2))

end = time.time()
print("Time elapsed: ", end - start)
