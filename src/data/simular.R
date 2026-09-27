# ---------------------------------------------------------------
# simular.R - Genera poblaciones sinteticas de ganado con AlphaSimR
# Proyecto: Seleccion Genomica de Precision en Ganado Vacuno
#
# Como correrlo:  Rscript src/data/simular.R
# Que genera:     data/processed/sim_n<N>/X_sim.csv  (SNPs 0/1/2)
#                 data/processed/sim_n<N>/y_sim.csv  (fenotipo + valor real)
#
# Los tamanos 125, 500 y 2000 son los mismos que usa el paper de
# Zhang et al. (2015), para que los resultados sean comparables.
# ---------------------------------------------------------------

library(AlphaSimR)

# --- PARAMETROS (lo unico que se toca) -------------------------
ESCENARIOS <- c(125, 500, 2000)   # tamanos de poblacion
N_SNPS     <- 10000               # marcadores del "chip"
N_QTL      <- 1000                # genes que SI afectan el rasgo
H2         <- 0.30                # heredabilidad
N_CROM     <- 29                  # cromosomas del ganado bovino
SEMILLA    <- 22200285            # para poder repetir el experimento
# ---------------------------------------------------------------

set.seed(SEMILLA)

snp_por_crom <- ceiling(N_SNPS / N_CROM)
qtl_por_crom <- ceiling(N_QTL  / N_CROM)
sitios_crom  <- snp_por_crom + qtl_por_crom + 50   # margen de seguridad

for (n in ESCENARIOS) {

  cat("\n=== Simulando poblacion de", n, "animales ===\n")
  t0 <- Sys.time()

  # 1. Poblacion fundadora: simula la historia evolutiva del ganado
  fundadores <- runMacs(
    nInd     = n,
    nChr     = N_CROM,
    segSites = sitios_crom,
    species  = "CATTLE"
  )

  # 2. Rasgo aditivo y chip de genotipado
  SP <- SimParam$new(fundadores)
  SP$addTraitA(nQtlPerChr = qtl_por_crom)
  SP$addSnpChip(nSnpPerChr = snp_por_crom)
  SP$setVarE(h2 = H2)

  # 3. Poblacion
  pop <- newPop(fundadores, simParam = SP)

  # 4. Extraccion
  X  <- pullSnpGeno(pop, simParam = SP)   # matriz 0/1/2
  y  <- pheno(pop)                        # fenotipo observado
  gv <- gv(pop)                           # valor genetico VERDADERO

  ids <- paste0("SIM", n, "_", sprintf("%05d", 1:n))

  X_out <- data.frame(id_animal = ids, X)
  colnames(X_out)[-1] <- sprintf("snp_%05d", 1:ncol(X))

  y_out <- data.frame(
    id_animal = ids,
    fenotipo  = as.numeric(y),
    valor_gv  = as.numeric(gv)
  )

  # 5. Guardado
  carpeta <- file.path("data", "processed", paste0("sim_n", n))
  dir.create(carpeta, recursive = TRUE, showWarnings = FALSE)

  write.csv(X_out, file.path(carpeta, "X_sim.csv"), row.names = FALSE)
  write.csv(y_out, file.path(carpeta, "y_sim.csv"), row.names = FALSE)

  cat("  animales:", nrow(X_out), "| SNPs:", ncol(X_out) - 1, "\n")
  cat("  h2 realizada:", round(var(gv) / var(y), 3), "\n")
  cat("  tiempo:", round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1), "seg\n")
  cat("  guardado en:", carpeta, "\n")
}

cat("\nListo.\n")
