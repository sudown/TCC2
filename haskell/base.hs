module Main where

minhaFuncao :: (Show a) => a -> String
minhaFuncao x = "Valor: " ++ show x

main = putStrLn (minhaFuncao 10)
