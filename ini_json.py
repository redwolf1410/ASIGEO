import json
import numpy as np

#scheduler = np.zeros((2,7,24))
#np.save("json_f/scheduler.npy",scheduler)
#print(scheduler)
#with open("json_f/scheduler.json", "w") as f:
#    json.dump(scheduler, f,indent=4)
estado_sondas = [{"b1":"down",
                        "b2":"normal"} for col in range(8)]


with open("json_f/states_sondas.json", "w") as f:
    json.dump(estado_sondas, f,indent=4)
