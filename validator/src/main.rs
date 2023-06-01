use std::env;
use std::fs::{File, self};
use std::io::Read;
use hugr;
use rmp_serde;

pub fn main() -> Result<(), hugr::hugr::ValidationError> {
    let args: Vec<String> = env::args().collect();
    let filename = &args[1];

    let mut f = File::open(&filename).expect("no file found");
    let metadata = fs::metadata(&filename).expect("unable to read metadata");
    let mut v = vec![0; metadata.len() as usize];
    f.read(&mut v).expect("buffer overflow");

    let hg: hugr::Hugr = rmp_serde::from_slice(&v[..]).unwrap();

    hg.validate()
}
