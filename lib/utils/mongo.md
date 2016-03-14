# SSH connection information:

 - Domain: python-limiere.rhcloud.com
 - Username: 561a4ac60c1e6686a50001d3
 - RSA key: C:\Users\Rudolf\.ssh\id_rsa

ssh 561a4ac60c1e6686a50001d3@python-limiere.rhcloud.com -L 27018:127.12.201.130:27017

----------------------------------
# Remote MongoDB information:

 - IP: 127.12.201.130
 - Port: 27017
 - Collection: /python

## Access:

 - username: admin
 - Password: bwz446YarDTq

----------------------------------

# Save remote database/collection:

`mongodump --host localhost:27018 -u admin -p bwz446YarDTq -d python -c raw_measures -v`


=======================================
# Load to local database/collection:

`mongorestore --host localhost:27017 -d dev -c raw_measures -drop dump/python/raw_measures.bson -v`

----------------------------------
# Example queries

#### oldest 3
```
db.getCollection('raw_measures').find({
	"result.0.time": {$gt: 0}
}).sort({
	"result.0.time": 1
}).limit(3)

db.getCollection('links').find({to_ip: "206.117.37.1",time: {$gt:1445112972, $lt:1445112973}})
```
#### Get a list wich nodes how many times were accessed by measuring:

	db.measure_times.aggregate([
	    {$group:{
	        _id:"$from",
	        measure_count:{$sum: 1}
	    }},
	    {$group:{
	        _id:"$measure_count",
	        nodes: {$push:"$_id"}
	    }}
	]).result

#### Export paralellmeasure node-access_time pairs into new collection:

	db.raw_measures.aggregate([
	    {$unwind: "$result"},
	    {$match:{"result.from":{$exists:true}}},
	    {$project: {
	        _id:0,
	        from:"$result.from",
	        time:"$result.time"
	    }},
	    {$out:"measure_times"}
	]).result

----------------------------------
# Min max mapreduce:

	var mapf = function() {

		for (var idx = 0; idx < this.result.length; idx++){

			if (this.result[idx] == null){

				return;

			}

			if (isNumber(this.result[idx].time))

				emit("max", this.result[idx].time);

		}

	};



	var reducef = function(key, times) {

		max = times[0]

		for (var idx = 0; idx < times.length; idx++) {

			if (times[idx] > max)

				max = times[idx]

		}

		return max

	};



	db.raw_measures.mapReduce(

		mapf,

		reducef,

		{ out: {inline:1} }

	)