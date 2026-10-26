/**
 * tests/helpers.js — utilitários partilhados.
 */
const path = require("path");
const fs = require("fs");

const DATA_DIR = path.join(__dirname, "..", "public", "data");

function lerJSON(nome) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, nome), "utf-8"));
}

module.exports = { lerJSON, DATA_DIR };
