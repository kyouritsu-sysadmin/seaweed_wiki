---
id: Seaweed-Message-Queue
title: "Seaweed Message Queue"
sidebar_label: "Seaweed Message Queue"
---

# Introduction

Seaweed Message Queue (SMQ) is a distributed messaging system built on top of SeaweedFS. It provides:

* Structured message : all messages need to have a schema
* Streamed publishing with async acknowledgements
* Messages are stored in Parquet files, for both streaming and batch reading
* Disaggregated storage
* Scalable stateless message brokers

# Architecture

The system consists of three main components:

1. **Message Queue Agent**: A gRPC server that provides a simplified interface for clients
2. **Message Queue Brokers**: Stateless brokers that handle message routing and storage
3. **SeaweedFS**: The underlying storage system that persists messages in Parquet format

```
  Publishers => gRPC Publish APIs => Agent => Brokers => Agent => gRPC Subscribe APIs => Subscribers
                                                 ^
                                                 |
                                                 v
                                             SeaweedFS
```

The Agent can be run either on the server side, or as a sidecar on each client.

# Features

## Core Features
* Structured Messages: SeaweedFS is used to store unstructured data files, while Seaweed Message Queue is used to store structured messages
* Messages stored in SeaweedFS can be converted into Parquet files, saving disk space with more efficient columnar compression
* The messages in Parquet files can be streamed via Seaweed messaging brokers
* The Parquet files can be read in batches directly from SeaweedFS

## Publishing Features
* Messages published successfully are acknowledged asynchronously
* Partition-based message routing
* Schema validation for message structure

## Subscribing Features
* Message consume offsets are tracked and persisted on the server side
* Consumer APIs can process messages in parallel while still ensuring serial processing of messages with the same key
* Configurable sliding window for concurrent message processing
* Ability to start consuming from specific timestamps or offsets

# Usage Examples

## Starting the Services

1. Start a Message Queue Broker:
```bash
weed mq.broker -port=17777 -master=localhost:9333
```

2. Start a Message Queue Agent:
```bash
weed mq.agent -port=16777 -broker=localhost:17777
```

## Defining Message Schema

Messages in SMQ must have a defined schema. Here's an example of defining a message type:

```go
type MyRecord struct {
    Key    []byte
    Field1 []byte
    Field2 string
    Field3 int32
    Field4 int64
    Field5 float32
    Field6 float64
    Field7 bool
}

func MyRecordType() *schema_pb.RecordType {
    return schema.RecordTypeBegin().
        WithField("key", schema.TypeBytes).
        WithField("field1", schema.TypeBytes).
        WithField("field2", schema.TypeString).
        WithField("field3", schema.TypeInt32).
        WithField("field4", schema.TypeInt64).
        WithField("field5", schema.TypeFloat).
        WithField("field6", schema.TypeDouble).
        WithField("field7", schema.TypeBoolean).
        RecordTypeEnd()
}
```

## Publishing Messages

```go
// Create a publish session
session, err := agent_client.NewPublishSession(
    "localhost:16777",  // agent address
    schema.NewSchema("my_namespace", "my_topic", MyRecordType()),
    6,                  // partition count
    "publisher1",       // client name
)

// Publish a message
myRecord := &MyRecord{
    Key:    []byte("key1"),
    Field1: []byte("value1"),
    Field2: "string value",
    Field3: 123,
    Field4: 456,
    Field5: 1.23,
    Field6: 4.56,
    Field7: true,
}

err := session.PublishMessageRecord(myRecord.Key, myRecord.ToRecordValue())
```

## Subscribing to Messages

```go
// Create a subscribe session
session, err := agent_client.NewSubscribeSession(
    "localhost:16777",  // agent address
    &agent_client.SubscribeOption{
        ConsumerGroup:           "my-group",
        ConsumerGroupInstanceId: "consumer1",
        Topic:                   topic.NewTopic("my_namespace", "topmy_topicic"),
        OffsetType:              schema_pb.OffsetType_RESUME_OR_EARLIEST,
        MaxSubscribedPartitions: 3,  // maximum number of partitions this consumer instance can subscribe
        SlidingWindowSize:       16, // concurrently process up-to 16 messages with different message key
    },
)

// Subscribe to messages
session.SubscribeMessageRecord(
    func(key []byte, recordValue *schema_pb.RecordValue) {
        record := FromRecordValue(recordValue)
        fmt.Printf("Received: %+v\n", record)
    },
    func() {
        fmt.Println("Subscription completed")
    },
)
```

# Configuration

## Broker Configuration
* `-port`: gRPC server port (default: 17777)
* `-master`: comma-separated master servers
* `-filerGroup`: share metadata with other filers in the same group
* `-dataCenter`: prefer volumes in this data center
* `-rack`: prefer volumes in this rack

## Agent Configuration
* `-port`: gRPC server port (default: 16777)
* `-broker`: comma-separated message queue brokers

