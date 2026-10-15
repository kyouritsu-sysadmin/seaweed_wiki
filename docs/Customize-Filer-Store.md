---
id: Customize-Filer-Store
title: "Customize Filer Store"
sidebar_label: "Customize Filer Store"
---

It is fairly easy if you need to store filer metadata with other data store.

Let's use "yourstore" as the chosen name.

Here are the steps:
1. Add a package under github.com/seaweedfs/seaweedfs/weed/filer/yourstore
2. Implement the filer.FilerStore interface
```
package filer

import (
	"errors"
)

type FilerStore interface {
	// GetName gets the name to locate the configuration in filer.toml file
	GetName() string
	// Initialize initializes the file store
	Initialize(configuration util.Configuration, prefix string) error
	InsertEntry(context.Context, *Entry) error
	UpdateEntry(context.Context, *Entry) (err error)
	// err == filer2.ErrNotFound if not found
	FindEntry(context.Context, util.FullPath) (entry *Entry, err error)
	DeleteEntry(context.Context, util.FullPath) (err error)
	DeleteFolderChildren(context.Context, util.FullPath) (err error)
	ListDirectoryEntries(ctx context.Context, dirPath util.FullPath, startFileName string, includeStartFile bool, limit int) ([]*Entry, error)
	ListDirectoryPrefixedEntries(ctx context.Context, dirPath util.FullPath, startFileName string, includeStartFile bool, limit int, prefix string) ([]*Entry, error)

	BeginTransaction(ctx context.Context) (context.Context, error)
	CommitTransaction(ctx context.Context) error
	RollbackTransaction(ctx context.Context) error

	KvPut(ctx context.Context, key []byte, value []byte) (err error)
	KvGet(ctx context.Context, key []byte) (value []byte, err error)
	KvDelete(ctx context.Context, key []byte) (err error)

	Shutdown()
}

```

3. Remember to add yourstore to the list of supported stores
```
func init() {
	filer2.Stores = append(filer2.Stores, &YourStore{})
}
```
4. Load yourstore. Just import it in  github.com/seaweedfs/seaweedfs/weed/server/filer_server.go
```
import (
	"net/http"
	"strconv"
	"github.com/seaweedfs/seaweedfs/weed/filer"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/cassandra"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/leveldb"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/mysql"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/postgres"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/redis"
	_ "github.com/seaweedfs/seaweedfs/weed/filer/yourstore"
        // ^^ add here
	"github.com/seaweedfs/seaweedfs/weed/security"
	"github.com/seaweedfs/seaweedfs/weed/glog"
)
```
5. Send a pull request!
