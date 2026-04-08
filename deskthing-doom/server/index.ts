import { DeskThing } from '@deskthing/server';

const start = async () => {
  console.log('Doom app started');
};

const stop = async () => {
  console.log('Doom app stopped');
};

const purge = async () => {
  console.log('Doom app purged');
};

DeskThing.on('start', start);
DeskThing.on('stop', stop);
DeskThing.on('purge', purge);
